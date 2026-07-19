//! Walk owned function bodies for meaningful returns and yields.

use ruff_python_ast::{Expr, Stmt};
use ruff_text_size::{Ranged, TextRange};

use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;

pub(crate) fn owned_return_shape(body: &[Stmt]) -> (Option<TextRange>, bool) {
    let mut meaningful_return: Option<TextRange> = None;
    let mut contains_yield = false;
    for statement in body {
        let (found, statement_yields) = return_shape(&ShapeNode::Stmt(statement));
        if meaningful_return.is_none() {
            meaningful_return = found;
        }
        contains_yield = contains_yield || statement_yields;
    }
    (meaningful_return, contains_yield)
}

fn return_shape(node: &ShapeNode<'_>) -> (Option<TextRange>, bool) {
    match node {
        ShapeNode::Stmt(Stmt::Return(inner)) => {
            let meaningful = match inner.value.as_deref() {
                None | Some(Expr::NoneLiteral(_)) => None,
                Some(_) => Some(inner.range()),
            };
            return (meaningful, false);
        }
        ShapeNode::Expr(Expr::Yield(_) | Expr::YieldFrom(_)) => return (None, true),
        ShapeNode::Stmt(Stmt::FunctionDef(_) | Stmt::ClassDef(_))
        | ShapeNode::Expr(Expr::Lambda(_)) => return (None, false),
        _ => {}
    }
    let mut meaningful_return: Option<TextRange> = None;
    let mut contains_yield = false;
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    children(node, &mut child_buffer);
    for child in child_buffer {
        let (found, child_yields) = return_shape(&child);
        if meaningful_return.is_none() {
            meaningful_return = found;
        }
        contains_yield = contains_yield || child_yields;
    }
    (meaningful_return, contains_yield)
}
