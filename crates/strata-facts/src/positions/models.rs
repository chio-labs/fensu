//! Position models shared across conversion entries.

/// A CPython-convention source position: 1-based line, 0-based UTF-8 byte column.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OffsetLocation {
    pub line: u32,
    pub column: u32,
}
