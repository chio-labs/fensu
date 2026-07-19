//! Project compact expressions, calls, and assignments from Ruff syntax.

use std::collections::BTreeSet;

use ruff_python_ast::{Expr, ExprContext, Stmt};
use ruff_text_size::Ranged;

use crate::facts::helpers::rule_authoring::references::strict_reference_parts;
use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::mapping::models::{MappingCallRow, MappingExpressionRow};
use crate::positions::models::LineIndex;

pub(crate) fn expression_row(expression: &Expr, source: &str) -> MappingExpressionRow {
    let (kind, child, string_value) = match expression {
        Expr::Name(_) => ("name", None, None),
        Expr::Attribute(inner) => (
            "attribute",
            Some(Box::new(expression_row(&inner.value, source))),
            None,
        ),
        Expr::Subscript(inner) => (
            "subscript",
            Some(Box::new(expression_row(&inner.value, source))),
            None,
        ),
        Expr::Call(inner) => (
            "call",
            Some(Box::new(expression_row(&inner.func, source))),
            None,
        ),
        Expr::StringLiteral(inner) => ("string", None, Some(inner.value.to_str().to_owned())),
        _ => ("other", None, None),
    };
    let range = expression.range();
    MappingExpressionRow {
        kind: kind.to_owned(),
        spelling: source
            .get(range.start().to_usize()..range.end().to_usize())
            .unwrap_or_default()
            .to_owned(),
        parts: strict_reference_parts(expression),
        child,
        string_value,
    }
}

pub(crate) fn owned_calls(
    root: ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
) -> Vec<MappingCallRow> {
    let mut calls = Vec::new();
    collect_owned_calls(root, index, source, &mut calls);
    calls
}

pub(crate) fn assigned_names(statement: &Stmt) -> Vec<String> {
    let mut names = BTreeSet::new();
    collect_assigned_names(ShapeNode::Stmt(statement), false, &mut names);
    names.into_iter().collect()
}

fn collect_owned_calls(
    node: ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
    calls: &mut Vec<MappingCallRow>,
) {
    if matches!(
        node,
        ShapeNode::Stmt(Stmt::FunctionDef(_) | Stmt::ClassDef(_))
            | ShapeNode::Expr(Expr::Lambda(_))
    ) {
        return;
    }
    if let ShapeNode::Expr(Expr::Call(call)) = node {
        let (line, _) = start_of(&node, index, source);
        calls.push(MappingCallRow {
            callee: expression_row(&call.func, source),
            line,
        });
    }
    let mut child_buffer = Vec::new();
    children(&node, &mut child_buffer);
    for child in child_buffer {
        collect_owned_calls(child, index, source, calls);
    }
}

fn collect_assigned_names(node: ShapeNode<'_>, nested: bool, names: &mut BTreeSet<String>) {
    match node {
        ShapeNode::Stmt(Stmt::FunctionDef(function)) if nested => {
            names.insert(function.name.as_str().to_owned());
            return;
        }
        ShapeNode::Stmt(Stmt::ClassDef(class)) if nested => {
            names.insert(class.name.as_str().to_owned());
            return;
        }
        ShapeNode::Expr(Expr::Lambda(_)) => return,
        ShapeNode::Expr(Expr::Name(name))
            if matches!(name.ctx, ExprContext::Store | ExprContext::Del) =>
        {
            names.insert(name.id.as_str().to_owned());
        }
        ShapeNode::Alias(alias) => {
            let bound = alias.asname.as_ref().map_or_else(
                || alias.name.as_str().split('.').next().unwrap_or_default(),
                |name| name.as_str(),
            );
            names.insert(bound.to_owned());
        }
        _ => {}
    }
    let mut child_buffer = Vec::new();
    children(&node, &mut child_buffer);
    for child in child_buffer {
        collect_assigned_names(child, true, names);
    }
}
