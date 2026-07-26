//! Resolve the line and column a node starts at.

use crate::positions::models::LineIndex;

use crate::syntax::types::ShapeNode;
pub fn start_of(node: &ShapeNode<'_>, index: &LineIndex, source: &str) -> (u32, u32) {
    crate::syntax::_helpers::spans::start_of(node, index, source)
}
