//! Resolve the full source span of a node.

use crate::positions::models::LineIndex;

use crate::syntax::types::ShapeNode;
pub fn span(node: &ShapeNode<'_>, index: &LineIndex, source: &str) -> Option<(u32, u32, u32, u32)> {
    crate::syntax::_helpers::spans::span(node, index, source)
}
