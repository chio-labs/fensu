//! Shared lookups over the breadth-first arena for metric extraction.

use std::collections::HashSet;

use ruff_python_ast::{Expr, Stmt, StmtFunctionDef};

use crate::constants;
use crate::facts::helpers::shape::nodes::ShapeNode;

pub(crate) fn function_positions(nodes: &[ShapeNode<'_>]) -> Vec<usize> {
    let mut positions: Vec<usize> = Vec::new();
    for want_async in [false, true] {
        for (position, node) in nodes.iter().enumerate() {
            if let ShapeNode::Stmt(Stmt::FunctionDef(function)) = node {
                if function.is_async == want_async {
                    positions.push(position);
                }
            }
        }
    }
    positions
}

pub(crate) fn function_at<'a>(
    nodes: &[ShapeNode<'a>],
    position: usize,
) -> Option<&'a StmtFunctionDef> {
    match nodes.get(position) {
        Some(ShapeNode::Stmt(Stmt::FunctionDef(function))) => Some(function),
        _ => None,
    }
}

pub(crate) fn dotted_call_name(expression: &Expr) -> Option<String> {
    match expression {
        Expr::Name(name) => Some(name.id.as_str().to_owned()),
        Expr::Attribute(attribute) => match dotted_call_name(&attribute.value) {
            Some(base) => Some(format!(
                "{base}{}{}",
                constants::MODULE_SEPARATOR,
                attribute.attr.as_str()
            )),
            None => Some(attribute.attr.as_str().to_owned()),
        },
        _ => None,
    }
}

pub(crate) fn nonreceiver_parameter_names(function: &StmtFunctionDef) -> HashSet<&str> {
    let parameters = &function.parameters;
    let mut names: HashSet<&str> = HashSet::new();
    for with_default in parameters
        .posonlyargs
        .iter()
        .chain(&parameters.args)
        .chain(&parameters.kwonlyargs)
    {
        names.insert(with_default.parameter.name.id.as_str());
    }
    if let Some(vararg) = &parameters.vararg {
        names.insert(vararg.name.id.as_str());
    }
    if let Some(kwarg) = &parameters.kwarg {
        names.insert(kwarg.name.id.as_str());
    }
    for receiver in constants::RECEIVER_NAMES {
        names.remove(receiver);
    }
    names
}

pub(crate) fn is_dunder_name(name: &str) -> bool {
    name.starts_with(constants::DUNDER_AFFIX) && name.ends_with(constants::DUNDER_AFFIX)
}

pub(crate) fn assigned_target_names<'a>(node: &ShapeNode<'a>) -> Vec<&'a str> {
    match node {
        ShapeNode::Stmt(Stmt::Assign(inner)) => inner
            .targets
            .iter()
            .filter_map(|target| match target {
                Expr::Name(name) => Some(name.id.as_str()),
                _ => None,
            })
            .collect(),
        ShapeNode::Stmt(Stmt::AnnAssign(inner)) => match &*inner.target {
            Expr::Name(name) => vec![name.id.as_str()],
            _ => Vec::new(),
        },
        _ => Vec::new(),
    }
}
