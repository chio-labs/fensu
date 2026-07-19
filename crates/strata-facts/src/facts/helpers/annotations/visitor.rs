//! Statement-order visitor collecting missing-annotation rows.

use std::collections::HashSet;

use ruff_python_ast::{Expr, ModModule, Parameter, Stmt, StmtClassDef, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::shape::breadth::breadth_first_nodes;
use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::{AnnotationRows, LocalAnnotationRow, NamedLocationRow};
use crate::positions::models::LineIndex;

pub(crate) struct AnnotationVisitor<'a> {
    index: &'a LineIndex,
    source: &'a str,
    class_depth: usize,
    function_scopes: Vec<HashSet<&'a str>>,
    rows: AnnotationRows,
}

impl<'a> AnnotationVisitor<'a> {
    pub(crate) fn collect(
        module: &'a ModModule,
        index: &'a LineIndex,
        source: &'a str,
    ) -> AnnotationRows {
        let mut visitor = AnnotationVisitor {
            index,
            source,
            class_depth: 0,
            function_scopes: Vec::new(),
            rows: AnnotationRows::default(),
        };
        for statement in &module.body {
            visitor.visit(&ShapeNode::Stmt(statement));
        }
        visitor.rows
    }

    fn visit(&mut self, node: &ShapeNode<'a>) {
        match node {
            ShapeNode::Stmt(Stmt::ClassDef(inner)) => self.visit_class(inner),
            ShapeNode::Stmt(Stmt::FunctionDef(inner)) => self.visit_function(inner, node),
            ShapeNode::Stmt(Stmt::Assign(_) | Stmt::AugAssign(_)) => self.record_locals(node),
            ShapeNode::Stmt(Stmt::AnnAssign(inner)) => {
                self.record_annotated_target(&inner.target);
            }
            _ => self.generic_visit(node),
        }
    }

    fn generic_visit(&mut self, node: &ShapeNode<'a>) {
        let mut child_buffer: Vec<ShapeNode<'a>> = Vec::new();
        children(node, &mut child_buffer);
        for child in child_buffer {
            if is_statement_container(&child) {
                self.visit(&child);
            }
        }
    }

    fn visit_class(&mut self, class: &'a StmtClassDef) {
        self.class_depth += 1;
        let enum_class = is_enum_class(class);
        for statement in &class.body {
            match statement {
                Stmt::FunctionDef(_) | Stmt::ClassDef(_) => {
                    self.visit(&ShapeNode::Stmt(statement));
                }
                Stmt::Assign(_) | Stmt::AugAssign(_) => {}
                Stmt::AnnAssign(inner) => {
                    if !enum_class {
                        self.record_annotated_target(&inner.target);
                    }
                }
                _ => self.visit(&ShapeNode::Stmt(statement)),
            }
        }
        self.class_depth -= 1;
    }

    fn visit_function(&mut self, function: &'a StmtFunctionDef, node: &ShapeNode<'a>) {
        self.record_function_annotations(function, node);
        self.function_scopes
            .push(annotated_parameter_names(function));
        for statement in &function.body {
            self.visit(&ShapeNode::Stmt(statement));
        }
        self.function_scopes.pop();
    }

    fn record_annotated_target(&mut self, target: &'a Expr) {
        if let (Some(scope), Expr::Name(name)) = (self.function_scopes.last_mut(), target) {
            scope.insert(name.id.as_str());
        }
    }

    fn record_function_annotations(&mut self, function: &'a StmtFunctionDef, node: &ShapeNode<'a>) {
        let exempt_name = self.exempt_receiver_name(function);
        for parameter in ordered_parameters(function) {
            let name = parameter.name.id.as_str();
            if parameter.annotation.is_some() || Some(name) == exempt_name {
                continue;
            }
            let (line, column) =
                start_of(&ShapeNode::Parameter(parameter), self.index, self.source);
            self.rows.parameters.push(NamedLocationRow {
                name: name.to_owned(),
                line,
                column,
            });
        }
        if function.returns.is_none() {
            let (line, column) = start_of(node, self.index, self.source);
            self.rows.returns.push(NamedLocationRow {
                name: function.name.id.as_str().to_owned(),
                line,
                column,
            });
        }
    }

    fn exempt_receiver_name(&self, function: &'a StmtFunctionDef) -> Option<&'a str> {
        if self.class_depth == 0 {
            return None;
        }
        let first = function
            .parameters
            .posonlyargs
            .first()
            .or_else(|| function.parameters.args.first())?;
        let name = first.parameter.name.id.as_str();
        constants::RECEIVER_NAMES.contains(&name).then_some(name)
    }

    fn record_locals(&mut self, node: &ShapeNode<'a>) {
        let ShapeNode::Stmt(statement) = node else {
            return;
        };
        if self.function_scopes.is_empty() {
            return;
        }
        let (targets, scalar_literal): (Vec<&'a Expr>, bool) = match statement {
            Stmt::Assign(inner) => {
                let scalar = inner.targets.len() == 1
                    && matches!(inner.targets.first(), Some(Expr::Name(_)))
                    && is_scalar_literal(&inner.value);
                (inner.targets.iter().collect(), scalar)
            }
            Stmt::AugAssign(inner) => (vec![&inner.target], false),
            _ => return,
        };
        for target in targets {
            let Expr::Name(name) = target else {
                continue;
            };
            let identifier = name.id.as_str();
            let known = identifier == constants::DISCARD_NAME
                || self
                    .function_scopes
                    .last()
                    .is_some_and(|scope| scope.contains(identifier));
            if known {
                continue;
            }
            let (line, column) = start_of(&ShapeNode::Expr(target), self.index, self.source);
            self.rows.locals.push(LocalAnnotationRow {
                name: identifier.to_owned(),
                line,
                column,
                scalar_literal,
            });
            if let Some(scope) = self.function_scopes.last_mut() {
                scope.insert(identifier);
            }
        }
    }
}

fn is_statement_container(node: &ShapeNode<'_>) -> bool {
    matches!(
        node,
        ShapeNode::Stmt(_)
            | ShapeNode::IfTail(_)
            | ShapeNode::ExceptHandler(_)
            | ShapeNode::MatchCase(_)
    )
}

fn ordered_parameters(function: &StmtFunctionDef) -> Vec<&Parameter> {
    let parameters = &function.parameters;
    let mut ordered: Vec<&Parameter> = Vec::new();
    for with_default in parameters.posonlyargs.iter().chain(&parameters.args) {
        ordered.push(&with_default.parameter);
    }
    for with_default in &parameters.kwonlyargs {
        ordered.push(&with_default.parameter);
    }
    if let Some(vararg) = &parameters.vararg {
        ordered.push(vararg);
    }
    if let Some(kwarg) = &parameters.kwarg {
        ordered.push(kwarg);
    }
    ordered
}

fn annotated_parameter_names(function: &StmtFunctionDef) -> HashSet<&str> {
    let mut names: HashSet<&str> = HashSet::new();
    for parameter in ordered_parameters(function) {
        let name = parameter.name.id.as_str();
        if parameter.annotation.is_some() || constants::RECEIVER_NAMES.contains(&name) {
            names.insert(name);
        }
    }
    names
}

fn is_enum_class(class: &StmtClassDef) -> bool {
    let Some(arguments) = &class.arguments else {
        return false;
    };
    arguments.args.iter().any(|base| match base {
        Expr::Name(name) => constants::ENUM_BASE_NAMES.contains(&name.id.as_str()),
        Expr::Attribute(attribute) => constants::ENUM_BASE_NAMES.contains(&attribute.attr.as_str()),
        _ => false,
    })
}

fn is_scalar_literal(expression: &Expr) -> bool {
    match expression {
        Expr::FString(_) => true,
        Expr::UnaryOp(inner) => {
            matches!(
                inner.op,
                ruff_python_ast::UnaryOp::UAdd | ruff_python_ast::UnaryOp::USub
            ) && is_scalar_literal(&inner.operand)
        }
        Expr::NumberLiteral(_)
        | Expr::StringLiteral(_)
        | Expr::BytesLiteral(_)
        | Expr::BooleanLiteral(_) => true,
        _ => false,
    }
}

pub(crate) fn module_variable_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<NamedLocationRow> {
    let mut rows: Vec<NamedLocationRow> = Vec::new();
    for statement in &module.body {
        variable_rows(
            statement,
            &constants::MODULE_EXEMPT_NAMES,
            index,
            source,
            &mut rows,
        );
    }
    rows
}

pub(crate) fn class_attribute_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<NamedLocationRow> {
    let mut rows: Vec<NamedLocationRow> = Vec::new();
    for node in breadth_first_nodes(module) {
        let ShapeNode::Stmt(Stmt::ClassDef(class)) = node else {
            continue;
        };
        if is_enum_class(class) {
            continue;
        }
        for statement in &class.body {
            variable_rows(
                statement,
                &constants::CLASS_EXEMPT_NAMES,
                index,
                source,
                &mut rows,
            );
        }
    }
    rows
}

fn variable_rows(
    statement: &Stmt,
    exempt_names: &[&str],
    index: &LineIndex,
    source: &str,
    rows: &mut Vec<NamedLocationRow>,
) {
    let targets: Vec<&Expr> = match statement {
        Stmt::Assign(inner) => inner.targets.iter().collect(),
        Stmt::AugAssign(inner) => vec![&inner.target],
        _ => return,
    };
    for target in targets {
        let Expr::Name(name) = target else {
            continue;
        };
        if exempt_names.contains(&name.id.as_str()) {
            continue;
        }
        let (line, column) = start_of(&ShapeNode::Expr(target), index, source);
        rows.push(NamedLocationRow {
            name: name.id.as_str().to_owned(),
            line,
            column,
        });
    }
}
