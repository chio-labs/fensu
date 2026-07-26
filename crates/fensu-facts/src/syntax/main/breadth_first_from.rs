//! Walk breadth first from one node.

use crate::syntax::types::ShapeNode;
pub fn breadth_first_from(root: ShapeNode<'_>) -> Vec<ShapeNode<'_>> {
    crate::syntax::_helpers::breadth::breadth_first_from(root)
}
