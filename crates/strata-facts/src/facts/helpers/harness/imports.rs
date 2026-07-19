//! Module binding index and conservative static reference resolution.

use std::collections::{HashMap, HashSet};

use ruff_python_ast::{Expr, ModModule, Stmt, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::shape::breadth::breadth_first_from;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::models::StaticReferenceRow;

pub(crate) struct BindingIndex<'a> {
    pub(crate) from_bindings: HashMap<&'a str, HashSet<StaticReferenceRow>>,
    pub(crate) module_bindings: HashMap<&'a str, HashSet<&'a str>>,
    pub(crate) module_shadowed: HashSet<&'a str>,
    pub(crate) literal_sequences: HashMap<&'a str, Vec<&'a Expr>>,
}

pub(crate) fn index_module_bindings(module: &ModModule) -> BindingIndex<'_> {
    let mut index = BindingIndex {
        from_bindings: HashMap::new(),
        module_bindings: HashMap::new(),
        module_shadowed: HashSet::new(),
        literal_sequences: HashMap::new(),
    };
    for statement in &module.body {
        match statement {
            Stmt::ImportFrom(inner) => {
                if inner.level != 0 {
                    continue;
                }
                let Some(module_name) = &inner.module else {
                    continue;
                };
                for alias in &inner.names {
                    if alias.name.as_str() == constants::WILDCARD_IMPORT_NAME {
                        continue;
                    }
                    let bound = alias
                        .asname
                        .as_ref()
                        .map(|asname| asname.as_str())
                        .unwrap_or_else(|| alias.name.as_str());
                    index
                        .from_bindings
                        .entry(bound)
                        .or_default()
                        .insert(StaticReferenceRow {
                            module_name: module_name.as_str().to_owned(),
                            symbol_name: alias.name.as_str().to_owned(),
                        });
                }
            }
            Stmt::Import(inner) => {
                for alias in &inner.names {
                    let (bound, module_name) = match &alias.asname {
                        Some(asname) => (asname.as_str(), alias.name.as_str()),
                        None => {
                            let first = alias
                                .name
                                .as_str()
                                .split(constants::MODULE_SEPARATOR)
                                .next()
                                .unwrap_or_default();
                            (first, first)
                        }
                    };
                    index
                        .module_bindings
                        .entry(bound)
                        .or_default()
                        .insert(module_name);
                }
            }
            _ => {
                let names = statement_bound_names(statement);
                for name in &names {
                    index.module_shadowed.insert(name);
                }
                if let Some(sequence) = literal_sequence(statement) {
                    for name in &names {
                        index
                            .literal_sequences
                            .entry(name)
                            .or_default()
                            .push(sequence);
                    }
                }
            }
        }
    }
    index
}

impl BindingIndex<'_> {
    pub(crate) fn resolve_expression(
        &self,
        expression: &Expr,
        shadowed: &HashSet<&str>,
    ) -> Option<StaticReferenceRow> {
        let parts = expression_parts(expression)?;
        let first = *parts.first()?;
        if shadowed.contains(first) || self.module_shadowed.contains(first) {
            return None;
        }
        if parts.len() == 1 {
            let references = self.from_bindings.get(first)?;
            if references.len() != 1 {
                return None;
            }
            return references.iter().next().cloned();
        }
        let modules = self.module_bindings.get(first)?;
        if modules.len() != 1 {
            return None;
        }
        let module_name = modules.iter().next()?;
        let mut qualified: Vec<&str> = vec![module_name];
        qualified.extend(&parts[1..parts.len() - 1]);
        Some(StaticReferenceRow {
            module_name: qualified.join(constants::MODULE_SEPARATOR),
            symbol_name: (*parts.last()?).to_owned(),
        })
    }

    pub(crate) fn is_rule_case_call(&self, expression: &Expr, shadowed: &HashSet<&str>) -> bool {
        let Expr::Call(call) = expression else {
            return false;
        };
        self.resolve_expression(&call.func, shadowed)
            .is_some_and(|reference| {
                reference.module_name == constants::STRATA_MODULE_NAME
                    && reference.symbol_name == constants::RULE_CASE_NAME
            })
    }
}

pub(crate) fn expression_parts(expression: &Expr) -> Option<Vec<&str>> {
    match expression {
        Expr::Name(name) => Some(vec![name.id.as_str()]),
        Expr::Attribute(attribute) => {
            let mut parts = expression_parts(&attribute.value)?;
            parts.push(attribute.attr.as_str());
            Some(parts)
        }
        _ => None,
    }
}

pub(crate) fn function_shadowed_names<'a>(
    function_statement: &'a Stmt,
    function: &'a StmtFunctionDef,
) -> HashSet<&'a str> {
    let mut names: HashSet<&'a str> = all_parameter_names(function).into_iter().collect();
    for node in breadth_first_from(ShapeNode::Stmt(function_statement)) {
        match &node {
            ShapeNode::Expr(Expr::Name(name)) => {
                if matches!(name.ctx, ruff_python_ast::ExprContext::Store) {
                    names.insert(name.id.as_str());
                }
            }
            ShapeNode::Stmt(Stmt::Import(inner)) => {
                for alias in &inner.names {
                    names.insert(bound_first_part(alias));
                }
            }
            ShapeNode::Stmt(Stmt::ImportFrom(inner)) => {
                for alias in &inner.names {
                    names.insert(bound_first_part(alias));
                }
            }
            ShapeNode::Stmt(Stmt::FunctionDef(inner))
                if !std::ptr::eq::<StmtFunctionDef>(inner, function) =>
            {
                names.insert(inner.name.as_str());
            }
            ShapeNode::Stmt(Stmt::ClassDef(inner)) => {
                names.insert(inner.name.as_str());
            }
            _ => {}
        }
    }
    names
}

fn bound_first_part(alias: &ruff_python_ast::Alias) -> &str {
    match &alias.asname {
        Some(asname) => asname.as_str(),
        None => alias
            .name
            .as_str()
            .split(constants::MODULE_SEPARATOR)
            .next()
            .unwrap_or_default(),
    }
}

pub(crate) fn all_parameter_names(function: &StmtFunctionDef) -> Vec<&str> {
    let parameters = &function.parameters;
    let mut names: Vec<&str> = Vec::new();
    for with_default in parameters
        .posonlyargs
        .iter()
        .chain(&parameters.args)
        .chain(&parameters.kwonlyargs)
    {
        names.push(with_default.parameter.name.id.as_str());
    }
    if let Some(vararg) = &parameters.vararg {
        names.push(vararg.name.id.as_str());
    }
    if let Some(kwarg) = &parameters.kwarg {
        names.push(kwarg.name.id.as_str());
    }
    names
}

fn statement_bound_names(statement: &Stmt) -> Vec<&str> {
    match statement {
        Stmt::FunctionDef(inner) => vec![inner.name.as_str()],
        Stmt::ClassDef(inner) => vec![inner.name.as_str()],
        Stmt::Assign(inner) => inner
            .targets
            .iter()
            .filter_map(|target| match target {
                Expr::Name(name) => Some(name.id.as_str()),
                _ => None,
            })
            .collect(),
        Stmt::AnnAssign(inner) => match &*inner.target {
            Expr::Name(name) => vec![name.id.as_str()],
            _ => Vec::new(),
        },
        _ => Vec::new(),
    }
}

fn literal_sequence(statement: &Stmt) -> Option<&Expr> {
    let value: Option<&Expr> = match statement {
        Stmt::Assign(inner) => Some(&inner.value),
        Stmt::AnnAssign(inner) => inner.value.as_deref(),
        _ => None,
    };
    value.filter(|inner| matches!(inner, Expr::List(_) | Expr::Tuple(_)))
}
