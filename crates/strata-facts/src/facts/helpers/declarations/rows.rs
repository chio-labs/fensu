//! Build classified module-declaration rows.

use ruff_python_ast::{Expr, ModModule, Stmt};

use crate::constants;
use crate::facts::helpers::naming::names::{
    assignment_target_names, is_all_assignment, is_dataclass_class, is_docstring_statement,
    is_exception_class, is_model_class, is_newtype, is_nonexecuting_guard,
    is_nonexecuting_import_guard, is_public_type_alias, is_rule_decorated_function,
    is_type_checking_import_block, is_type_class,
};
use crate::facts::helpers::shape::breadth::breadth_first_from;
use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::helpers::shape::statement_children::push_clause_orelse;
use crate::facts::models::{
    ModuleDeclarationRows, ModuleStatementRow, NamedCallRow, TypeDeclarationRow,
};
use crate::positions::models::LineIndex;

pub(crate) fn collect_class_rows(
    breadth_nodes: &[ShapeNode<'_>],
    index: &LineIndex,
    source: &str,
    rows: &mut ModuleDeclarationRows,
) {
    for node in breadth_nodes {
        let ShapeNode::Stmt(Stmt::ClassDef(class)) = node else {
            continue;
        };
        let location = start_of(node, index, source);
        if is_model_class(class) {
            rows.model_locations.push(location);
        }
        if is_type_class(class) {
            rows.type_declarations.push(TypeDeclarationRow {
                line: location.0,
                column: location.1,
                private: class
                    .name
                    .as_str()
                    .starts_with(constants::PRIVATE_NAME_PREFIX),
            });
        }
        if is_exception_class(class) {
            rows.exception_locations.push(location);
        }
    }
}

pub(crate) fn collect_statement_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
    rows: &mut ModuleDeclarationRows,
) {
    let mut body: &[Stmt] = &module.body;
    if body.first().is_some_and(is_docstring_statement) {
        body = &body[1..];
    }
    for statement in body {
        let node = ShapeNode::Stmt(statement);
        let (line, column) = start_of(&node, index, source);
        let class = match statement {
            Stmt::ClassDef(inner) => Some(inner),
            _ => None,
        };
        let all_assignment = is_all_assignment(statement);
        rows.statements.push(ModuleStatementRow {
            line,
            column,
            import_statement: matches!(statement, Stmt::Import(_) | Stmt::ImportFrom(_)),
            assignment_statement: matches!(statement, Stmt::Assign(_) | Stmt::AnnAssign(_)),
            explicit_type_alias: matches!(statement, Stmt::TypeAlias(_)),
            type_checking_import_block: is_type_checking_import_block(statement),
            model_class: class.is_some_and(is_model_class),
            type_class: class.is_some_and(is_type_class),
            exception_class: class.is_some_and(is_exception_class),
            assignment_target_names: assignment_target_names(statement)
                .into_iter()
                .map(str::to_owned)
                .collect(),
            function_name: function_name(statement),
            class_name: class.map(|inner| inner.name.as_str().to_owned()),
            dataclass_class: class.is_some_and(is_dataclass_class),
            docstring_statement: is_docstring_statement(statement),
            all_assignment,
            rule_decorated_function: is_rule_decorated_function(statement),
            nonexecuting_import_guard: is_nonexecuting_import_guard(statement),
        });
        if all_assignment {
            rows.all_assignment_locations.push((line, column));
        }
    }
}

pub(crate) fn collect_alias_rows(
    breadth_nodes: &[ShapeNode<'_>],
    index: &LineIndex,
    source: &str,
    rows: &mut ModuleDeclarationRows,
) {
    let matchers: [fn(&Stmt) -> bool; 3] = [
        is_assign_statement,
        is_ann_assign_statement,
        is_type_alias_statement,
    ];
    for matcher in matchers {
        for node in breadth_nodes {
            let ShapeNode::Stmt(statement) = node else {
                continue;
            };
            if !matcher(statement) {
                continue;
            }
            if is_public_type_alias(statement) || is_newtype(statement) {
                let (line, column) = start_of(node, index, source);
                rows.type_declarations.push(TypeDeclarationRow {
                    line,
                    column,
                    private: false,
                });
            }
        }
    }
}

pub(crate) fn is_assign_statement(statement: &Stmt) -> bool {
    matches!(statement, Stmt::Assign(_))
}

pub(crate) fn is_ann_assign_statement(statement: &Stmt) -> bool {
    matches!(statement, Stmt::AnnAssign(_))
}

pub(crate) fn is_type_alias_statement(statement: &Stmt) -> bool {
    matches!(statement, Stmt::TypeAlias(_))
}

pub(crate) fn function_name(statement: &Stmt) -> Option<String> {
    match statement {
        Stmt::FunctionDef(inner) => Some(inner.name.as_str().to_owned()),
        _ => None,
    }
}

pub(crate) fn is_pure_reexport(module: &ModModule) -> bool {
    let mut saw_import = false;
    let mut saw_all = false;
    for statement in &module.body {
        if is_docstring_statement(statement) {
            continue;
        }
        if let Stmt::ImportFrom(inner) = statement {
            if inner
                .module
                .as_ref()
                .is_some_and(|name| name.as_str() == constants::FUTURE_MODULE_NAME)
            {
                continue;
            }
        }
        if matches!(statement, Stmt::Import(_) | Stmt::ImportFrom(_)) {
            saw_import = true;
            continue;
        }
        if is_all_assignment(statement) {
            saw_all = true;
            continue;
        }
        return false;
    }
    saw_import && saw_all
}

pub(crate) fn collect_import_time_calls(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
    rows: &mut ModuleDeclarationRows,
) {
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    children(&ShapeNode::Module(module), &mut child_buffer);
    for child in child_buffer {
        import_time_calls_in(&child, index, source, rows);
    }
}

pub(crate) fn import_time_calls_in(
    node: &ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
    rows: &mut ModuleDeclarationRows,
) {
    match node {
        ShapeNode::Stmt(Stmt::FunctionDef(_)) | ShapeNode::Expr(Expr::Lambda(_)) => return,
        ShapeNode::Stmt(Stmt::If(inner)) if is_nonexecuting_guard(&inner.test) => {
            let mut orelse: Vec<ShapeNode<'_>> = Vec::new();
            push_clause_orelse(&inner.elif_else_clauses, &mut orelse);
            for child in orelse {
                import_time_calls_in(&child, index, source, rows);
            }
            return;
        }
        ShapeNode::IfTail(clauses) => {
            if let Some(first) = clauses.first() {
                if first.test.as_ref().is_some_and(is_nonexecuting_guard) {
                    let mut orelse: Vec<ShapeNode<'_>> = Vec::new();
                    push_clause_orelse(&clauses[1..], &mut orelse);
                    for child in orelse {
                        import_time_calls_in(&child, index, source, rows);
                    }
                    return;
                }
            }
        }
        ShapeNode::Stmt(Stmt::Expr(inner)) => {
            if matches!(&*inner.value, Expr::Call(_)) {
                rows.import_time_call_locations
                    .push(start_of(node, index, source));
                return;
            }
        }
        _ => {}
    }
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    children(node, &mut child_buffer);
    for child in child_buffer {
        import_time_calls_in(&child, index, source, rows);
    }
}

pub(crate) fn imported_main_entry_names(module: &ModModule) -> Vec<String> {
    let mut names: Vec<String> = Vec::new();
    for statement in &module.body {
        let Stmt::ImportFrom(inner) = statement else {
            continue;
        };
        let Some(module_name) = &inner.module else {
            continue;
        };
        let has_main_part = module_name
            .as_str()
            .split(constants::MODULE_SEPARATOR)
            .any(|part| part == constants::MAIN_ROLE_NAME);
        if !has_main_part {
            continue;
        }
        for alias in &inner.names {
            let bound = alias
                .asname
                .as_ref()
                .map(|asname| asname.as_str())
                .unwrap_or_else(|| alias.name.as_str());
            names.push(bound.to_owned());
        }
    }
    names
}

pub(crate) fn main_call_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<NamedCallRow> {
    let main_statement: Option<&Stmt> = module.body.iter().find(|statement| {
        matches!(
            statement,
            Stmt::FunctionDef(inner) if inner.name.as_str() == constants::MAIN_ROLE_NAME
        )
    });
    let Some(statement) = main_statement else {
        return Vec::new();
    };
    let mut calls: Vec<NamedCallRow> = Vec::new();
    for node in breadth_first_from(ShapeNode::Stmt(statement)) {
        let ShapeNode::Expr(Expr::Call(call)) = node else {
            continue;
        };
        let (line, column) = start_of(&node, index, source);
        let name = match &*call.func {
            Expr::Name(inner) => Some(inner.id.as_str().to_owned()),
            _ => None,
        };
        calls.push(NamedCallRow { line, column, name });
    }
    calls
}

pub(crate) fn dataclass_rows(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<crate::facts::models::DataclassRow> {
    let mut rows: Vec<crate::facts::models::DataclassRow> = Vec::new();
    for statement in &module.body {
        let Stmt::ClassDef(class) = statement else {
            continue;
        };
        let decorator = class.decorator_list.iter().find(|candidate| {
            crate::facts::helpers::naming::names::decorator_name(&candidate.expression)
                .ends_with(crate::constants::DATACLASS_DECORATOR_NAME)
        });
        let Some(decorator) = decorator else {
            continue;
        };
        let shape_expression = match &decorator.expression {
            Expr::Call(call) => &*call.func,
            other => other,
        };
        let shape_name = crate::facts::helpers::naming::names::decorator_name(shape_expression);
        let mut field_names: Vec<String> = Vec::new();
        for body_statement in &class.body {
            if let Stmt::AnnAssign(inner) = body_statement {
                if let Expr::Name(name) = &*inner.target {
                    field_names.push(name.id.as_str().to_owned());
                }
            }
        }
        let (line, column) = start_of(&ShapeNode::Stmt(statement), index, source);
        rows.push(crate::facts::models::DataclassRow {
            name: class.name.as_str().to_owned(),
            line,
            column,
            field_names,
            frozen: dataclass_call_is_frozen(&decorator.expression),
            shape_candidate: shape_name == crate::constants::DATACLASS_DECORATOR_NAME,
        });
    }
    rows
}

fn dataclass_call_is_frozen(expression: &Expr) -> bool {
    let Expr::Call(call) = expression else {
        return false;
    };
    for keyword in &call.arguments.keywords {
        let named_frozen = keyword
            .arg
            .as_ref()
            .is_some_and(|name| name.as_str() == crate::constants::FROZEN_KEYWORD_NAME);
        if !named_frozen {
            continue;
        }
        return match &keyword.value {
            Expr::BooleanLiteral(literal) => literal.value,
            _ => false,
        };
    }
    false
}
