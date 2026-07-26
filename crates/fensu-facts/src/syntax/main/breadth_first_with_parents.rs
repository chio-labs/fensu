//! Walk breadth first, pairing nodes with parents.

use ruff_python_ast::ModModule;

use crate::syntax::types::ShapeNode;
pub fn breadth_first_with_parents(module: &ModModule) -> (Vec<ShapeNode<'_>>, Vec<Option<usize>>) {
    crate::syntax::_helpers::breadth::breadth_first_with_parents(module)
}
