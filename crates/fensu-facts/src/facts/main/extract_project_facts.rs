//! Extract project-resolvable call and function contracts.

use ruff_python_ast::{ModModule, Stmt};

use crate::facts::helpers::project::calls::{
    discarded_call_rows, project_function_meaningful_result,
};
use crate::facts::models::{DiscardedCallRow, ProjectFunctionRow};
use crate::positions::models::LineIndex;

/// Return top-level function contracts and resolvable discarded calls.
pub fn extract_project_facts(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> (Vec<ProjectFunctionRow>, Vec<DiscardedCallRow>) {
    let functions: Vec<ProjectFunctionRow> = module
        .body
        .iter()
        .filter_map(|statement| match statement {
            Stmt::FunctionDef(inner) => Some(ProjectFunctionRow {
                name: inner.name.as_str().to_owned(),
                meaningful_result: project_function_meaningful_result(inner),
            }),
            _ => None,
        })
        .collect();
    (functions, discarded_call_rows(module, index, source))
}
