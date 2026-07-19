//! Byte-to-line indexing for stable source ranges.

use std::ops::Range;

use crate::markdown::models::SourceRange;

#[derive(Debug)]
pub(crate) struct LineIndex {
    line_starts: Vec<usize>,
    source_len: usize,
}

impl LineIndex {
    pub(crate) fn new(source: &str) -> Self {
        let mut line_starts = vec![0];
        for (offset, byte) in source.bytes().enumerate() {
            if byte == b'\n' {
                line_starts.push(offset + 1);
            }
        }
        Self {
            line_starts,
            source_len: source.len(),
        }
    }

    pub(crate) fn line_number(&self, offset: usize) -> usize {
        let bounded = offset.min(self.source_len);
        self.line_starts.partition_point(|start| *start <= bounded)
    }

    pub(crate) fn source_range(&self, range: Range<usize>) -> SourceRange {
        let start_byte = range.start.min(self.source_len);
        let end_byte = range.end.clamp(start_byte, self.source_len);
        let start_line = self.line_number(start_byte);
        let end_line = if end_byte == start_byte {
            start_line
        } else {
            self.line_number(end_byte - 1) + 1
        };
        SourceRange {
            start_byte,
            end_byte,
            start_line,
            end_line,
        }
    }
}
