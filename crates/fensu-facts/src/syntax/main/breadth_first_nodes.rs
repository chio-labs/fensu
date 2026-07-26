//! Walk a module breadth first.

use ruff_python_ast::ModModule;

use crate::syntax::types::ShapeNode;
pub fn breadth_first_nodes(module: &ModModule) -> Vec<ShapeNode<'_>> {
    crate::syntax::_helpers::breadth::breadth_first_nodes(module)
}
