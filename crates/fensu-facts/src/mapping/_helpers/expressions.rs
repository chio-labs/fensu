//! Project compact expressions, calls, and assignments from Ruff syntax.

use std::collections::BTreeSet;

use ruff_python_ast::{Expr, ExprContext, Stmt};
use ruff_text_size::Ranged;

use crate::mapping::models::{MappingCallRow, MappingExpressionRow};
use crate::positions::models::LineIndex;
use crate::syntax::main::children::children;
use crate::syntax::main::start_of::start_of;
use crate::syntax::main::strict_reference_parts::strict_reference_parts;
use crate::syntax::types::ShapeNode;

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
    collect_owned_calls(root, index, source, Vec::new())
}

pub(crate) fn assigned_names(statement: &Stmt) -> Vec<String> {
    let names = collect_assigned_names(ShapeNode::Stmt(statement), false, BTreeSet::new());
    names.into_iter().collect()
}

fn collect_owned_calls(
    node: ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
    mut calls: Vec<MappingCallRow>,
) -> Vec<MappingCallRow> {
    if matches!(
        node,
        ShapeNode::Stmt(Stmt::FunctionDef(_) | Stmt::ClassDef(_))
            | ShapeNode::Expr(Expr::Lambda(_))
    ) {
        return calls;
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
        calls = collect_owned_calls(child, index, source, calls);
    }
    calls
}

fn collect_assigned_names(
    node: ShapeNode<'_>,
    nested: bool,
    mut names: BTreeSet<String>,
) -> BTreeSet<String> {
    match node {
        ShapeNode::Stmt(Stmt::FunctionDef(function)) if nested => {
            names.insert(function.name.as_str().to_owned());
            return names;
        }
        ShapeNode::Stmt(Stmt::ClassDef(class)) if nested => {
            names.insert(class.name.as_str().to_owned());
            return names;
        }
        ShapeNode::Expr(Expr::Lambda(_)) => return names,
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
        names = collect_assigned_names(child, true, names);
    }
    names
}
