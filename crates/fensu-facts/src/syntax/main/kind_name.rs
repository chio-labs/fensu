//! Name the syntax kind of a node.

use crate::syntax::types::ShapeNode;
pub fn kind_name(node: &ShapeNode<'_>) -> &'static str {
    crate::syntax::_helpers::nodes::kind_name(node)
}
