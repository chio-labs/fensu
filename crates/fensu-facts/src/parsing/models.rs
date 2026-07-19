//! Parse failure models shared across parsing entries.

/// A strict-parse rejection at a 1-based line and 0-based UTF-8 byte column.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParseFailure {
    pub line: u32,
    pub column: u32,
    pub message: String,
}
