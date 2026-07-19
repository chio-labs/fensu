//! Index newline-delimited line start offsets over raw source bytes.

use crate::constants;

pub(crate) fn line_start_offsets(source: &str) -> Vec<usize> {
    let mut starts = vec![0];
    for (index, byte) in source.bytes().enumerate() {
        if byte == constants::NEWLINE_BYTE {
            starts.push(index + 1);
        }
    }
    starts
}
