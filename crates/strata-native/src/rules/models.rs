//! Shared native core-rule output models.

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeFaultRow {
    pub code: &'static str,
    pub line: u32,
    pub column: u32,
    pub message: String,
}
