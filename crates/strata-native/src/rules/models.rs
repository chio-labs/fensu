//! Shared native core-rule output models.

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeFaultRow {
    pub code: String,
    pub line: u32,
    pub column: u32,
    pub message: Option<String>,
}
