//! Enumerate the CPython-shaped node stream in breadth-first order.

use std::collections::VecDeque;

use ruff_python_ast::{ModModule, PythonVersion};

use crate::facts::helpers::shape::children::children;
use crate::facts::helpers::shape::nodes::{kind_name, ShapeNode};
use crate::facts::helpers::shape::spans::span;
use crate::facts::models::LocatedNode;
use crate::parsing::main::parse_strict::parse_strict;
use crate::parsing::models::ParseFailure;
use crate::positions::main::index_lines::index_lines;

/// Return every CPython-equivalent node with kind and span in BFS order.
pub fn enumerate_nodes(
    source: &str,
    version: PythonVersion,
) -> Result<Vec<LocatedNode>, ParseFailure> {
    let parsed = parse_strict(source, version)?;
    let module: &ModModule = parsed.syntax();
    let index = index_lines(source);
    let mut located: Vec<LocatedNode> = Vec::new();
    let mut pending: VecDeque<ShapeNode<'_>> = VecDeque::new();
    pending.push_back(ShapeNode::Module(module));
    let mut child_buffer: Vec<ShapeNode<'_>> = Vec::new();
    while let Some(node) = pending.pop_front() {
        located.push(LocatedNode {
            kind: kind_name(&node),
            span: span(&node, &index, source),
        });
        child_buffer.clear();
        children(&node, &mut child_buffer);
        for child in &child_buffer {
            pending.push_back(*child);
        }
    }
    Ok(located)
}
