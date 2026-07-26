//! Collect the direct children of one syntax node.

use crate::syntax::types::ShapeNode;
pub fn children<'a>(node: &ShapeNode<'a>, out: &mut Vec<ShapeNode<'a>>) {
    crate::syntax::_helpers::children::children(node, out)
}
