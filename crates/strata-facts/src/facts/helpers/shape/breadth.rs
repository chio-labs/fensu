//! Breadth-first traversal over the CPython-shaped tree.

use std::collections::VecDeque;

use ruff_python_ast::ModModule;

use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::ShapeNode;

pub(crate) fn breadth_first_nodes(module: &ModModule) -> Vec<ShapeNode<'_>> {
    breadth_first_from(ShapeNode::Module(module))
}

pub(crate) fn breadth_first_from(root: ShapeNode<'_>) -> Vec<ShapeNode<'_>> {
    let mut nodes: Vec<ShapeNode<'_>> = Vec::new();
    let mut pending: VecDeque<ShapeNode<'_>> = VecDeque::new();
    pending.push_back(root);
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    while let Some(node) = pending.pop_front() {
        child_buffer.clear();
        children(&node, &mut child_buffer);
        for child in &child_buffer {
            pending.push_back(*child);
        }
        nodes.push(node);
    }
    nodes
}

pub(crate) fn breadth_first_with_parents(
    module: &ModModule,
) -> (Vec<ShapeNode<'_>>, Vec<Option<usize>>) {
    let mut nodes: Vec<ShapeNode<'_>> = Vec::new();
    let mut parents: Vec<Option<usize>> = Vec::new();
    let mut pending: VecDeque<(ShapeNode<'_>, Option<usize>)> = VecDeque::new();
    pending.push_back((ShapeNode::Module(module), None));
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    while let Some((node, parent)) = pending.pop_front() {
        let position = nodes.len();
        nodes.push(node);
        parents.push(parent);
        child_buffer.clear();
        children(&node, &mut child_buffer);
        for child in &child_buffer {
            pending.push_back((*child, Some(position)));
        }
    }
    (nodes, parents)
}
