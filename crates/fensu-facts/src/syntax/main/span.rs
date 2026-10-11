//! Resolve the full source span of a node.

use crate::positions::models::{LineIndex, SourceSpan};

use crate::syntax::types::ShapeNode;
pub fn span(node: &ShapeNode<'_>, index: &LineIndex, source: &str) -> Option<SourceSpan> {
    crate::syntax::_helpers::spans::span(node, index, source)
}
