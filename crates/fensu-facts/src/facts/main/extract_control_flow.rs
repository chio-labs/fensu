//! Extract conditional and comprehension control-flow rows.

use ruff_python_ast::{ModModule, Stmt};

use crate::facts::helpers::control::conditionals::{
    complex_comprehension_rows, function_conditional_rows, test_conditional_rows,
};
use crate::facts::models::ControlFlowRows;
use crate::positions::models::LineIndex;

/// Return function conditionals, complex comprehensions, and top-level test conditionals.
pub fn extract_control_flow(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> ControlFlowRows {
    let definitions: Vec<&Stmt> = module
        .body
        .iter()
        .filter(|statement| matches!(statement, Stmt::FunctionDef(_) | Stmt::ClassDef(_)))
        .collect();
    ControlFlowRows {
        function_conditionals: function_conditional_rows(module, index, source),
        complex_comprehensions: complex_comprehension_rows(module, index, source),
        top_level_test_conditionals: test_conditional_rows(&definitions, index, source),
    }
}
