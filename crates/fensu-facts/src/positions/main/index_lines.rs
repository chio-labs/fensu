//! Build a reusable line-start index for repeated offset conversion.

use crate::positions::helpers::line_index;
use crate::positions::models::LineIndex;

/// Return a reusable line index over the raw source bytes.
pub fn index_lines(source: &str) -> LineIndex {
    LineIndex::new(line_index::line_start_offsets(source), source.len())
}
