//! Extract direct mutations resolving to outer-scope state.

use ruff_python_ast::ModModule;

use crate::facts::helpers::state::resolution::outer_mutation_ranges;
use crate::facts::models::SourceRangeRow;
use crate::positions::models::LineIndex;

/// Return end-exclusive ranges for mutations owned by an outer scope.
pub fn extract_outer_state_mutations(module: &ModModule, index: &LineIndex) -> Vec<SourceRangeRow> {
    let mut rows: Vec<SourceRangeRow> = Vec::new();
    for range in outer_mutation_ranges(module) {
        let start = index.locate(range.start().to_usize());
        let end = index.locate(range.end().to_usize());
        rows.push(SourceRangeRow {
            start_line: start.line,
            start_column: start.column,
            start_offset: u32::try_from(range.start().to_usize()).unwrap_or(u32::MAX),
            end_line: end.line,
            end_column: end.column,
            end_offset: u32::try_from(range.end().to_usize()).unwrap_or(u32::MAX),
        });
    }
    rows
}
