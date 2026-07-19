//! Position models shared across conversion entries.

/// A CPython-convention source position: 1-based line, 0-based UTF-8 byte column.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OffsetLocation {
    pub line: u32,
    pub column: u32,
}

/// A reusable index of line-start byte offsets for one source snapshot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LineIndex {
    starts: Vec<usize>,
    source_length: usize,
}

impl LineIndex {
    /// Build the index from newline-delimited line starts.
    pub fn new(starts: Vec<usize>, source_length: usize) -> Self {
        Self {
            starts,
            source_length,
        }
    }

    /// Return the CPython-convention location for one clamped byte offset.
    pub fn locate(&self, offset: usize) -> OffsetLocation {
        let clamped = offset.min(self.source_length);
        let line_number = self.starts.partition_point(|start| *start <= clamped);
        let line_start = self
            .starts
            .get(line_number - 1)
            .copied()
            .unwrap_or_default();
        OffsetLocation {
            line: u32::try_from(line_number).unwrap_or(u32::MAX),
            column: u32::try_from(clamped - line_start).unwrap_or(u32::MAX),
        }
    }

    /// Return the byte offset where the located line begins.
    pub fn line_start(&self, offset: usize) -> usize {
        let clamped = offset.min(self.source_length);
        let line_number = self.starts.partition_point(|start| *start <= clamped);
        self.starts
            .get(line_number - 1)
            .copied()
            .unwrap_or_default()
    }
}
