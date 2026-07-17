//! Lexical ownership over the shared breadth-first arena.

use ruff_python_ast::Stmt;

use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::shape::spans::start_of;
use crate::facts::models::DefinitionIdentityRow;
use crate::positions::models::LineIndex;

pub(crate) fn ancestor_positions(parents: &[Option<usize>], position: usize) -> Vec<usize> {
    let mut ancestors = Vec::new();
    let mut current = parents[position];
    while let Some(parent) = current {
        ancestors.push(parent);
        current = parents[parent];
    }
    ancestors
}

pub(crate) fn enclosing_classes(
    nodes: &[ShapeNode<'_>],
    parents: &[Option<usize>],
    position: usize,
    index: &LineIndex,
    source: &str,
) -> Vec<DefinitionIdentityRow> {
    ancestor_positions(parents, position)
        .into_iter()
        .filter_map(|ancestor| class_identity(&nodes[ancestor], index, source))
        .collect()
}

pub(crate) fn enclosing_functions(
    nodes: &[ShapeNode<'_>],
    parents: &[Option<usize>],
    position: usize,
    index: &LineIndex,
    source: &str,
) -> Vec<DefinitionIdentityRow> {
    ancestor_positions(parents, position)
        .into_iter()
        .filter_map(|ancestor| function_identity(&nodes[ancestor], index, source))
        .collect()
}

pub(crate) fn class_identity(
    node: &ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
) -> Option<DefinitionIdentityRow> {
    let ShapeNode::Stmt(Stmt::ClassDef(class)) = node else {
        return None;
    };
    let (line, column) = start_of(node, index, source);
    Some(DefinitionIdentityRow {
        name: class.name.as_str().to_owned(),
        line,
        column,
    })
}

pub(crate) fn function_identity(
    node: &ShapeNode<'_>,
    index: &LineIndex,
    source: &str,
) -> Option<DefinitionIdentityRow> {
    let ShapeNode::Stmt(Stmt::FunctionDef(function)) = node else {
        return None;
    };
    let (line, column) = start_of(node, index, source);
    Some(DefinitionIdentityRow {
        name: function.name.as_str().to_owned(),
        line,
        column,
    })
}

pub(crate) fn has_loop_ancestor(
    nodes: &[ShapeNode<'_>],
    parents: &[Option<usize>],
    position: usize,
) -> bool {
    ancestor_positions(parents, position)
        .into_iter()
        .any(|ancestor| {
            matches!(
                nodes[ancestor],
                ShapeNode::Stmt(Stmt::For(_) | Stmt::While(_))
            )
        })
}
