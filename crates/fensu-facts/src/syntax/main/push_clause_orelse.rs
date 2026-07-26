//! Push the else clauses of an if statement.

use ruff_python_ast::ElifElseClause;

use crate::syntax::_helpers::statement_children::ClauseOutput;
use crate::syntax::types::ShapeNode;

pub fn push_clause_orelse<'a>(clauses: &'a [ElifElseClause], out: &mut Vec<ShapeNode<'a>>) {
    ClauseOutput { out }.collect(clauses);
}
