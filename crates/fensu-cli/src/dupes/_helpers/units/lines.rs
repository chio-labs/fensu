//! Byte-offset to 1-based line lookup shared by the language extractors.

pub(crate) struct LineIndex {
    starts: Vec<usize>,
}

impl LineIndex {
    pub(crate) fn new(text: &str) -> Self {
        let mut starts = vec![0];
        starts.extend(
            text.bytes()
                .enumerate()
                .filter(|(_, byte)| *byte == b'\n')
                .map(|(offset, _)| offset + 1),
        );
        Self { starts }
    }

    pub(crate) fn line(&self, offset: usize) -> usize {
        self.starts.partition_point(|start| *start <= offset)
    }

    /// Line of the last byte of an exclusive `[start, end)` range.
    pub(crate) fn end_line(&self, start: usize, end: usize) -> usize {
        self.line(end.saturating_sub(1).max(start))
    }
}
