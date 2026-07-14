//! Convert a byte offset into a CPython-convention source position.

use crate::positions::helpers::line_index;
use crate::positions::models::OffsetLocation;

/// Return the 1-based line and 0-based UTF-8 byte column for a byte offset.
pub fn locate_offset(source: &str, offset: usize) -> OffsetLocation {
    let clamped = offset.min(source.len());
    let starts = line_index::line_start_offsets(source);
    let line_number = starts.partition_point(|start| *start <= clamped);
    let line_start = starts.get(line_number - 1).copied().unwrap_or_default();
    OffsetLocation {
        line: u32::try_from(line_number).unwrap_or(u32::MAX),
        column: u32::try_from(clamped - line_start).unwrap_or(u32::MAX),
    }
}
