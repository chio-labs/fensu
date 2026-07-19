//! Closed classifications emitted by corpus loading.

/// Stable corpus-loading diagnostic classification.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CorpusDiagnosticKind {
    ReadFailure,
    ContentChangedDuringLoad,
    InvalidUtf8,
    MissingOrEmptyTitle,
    FirstHeadingNotH1,
    MultipleH1Titles,
}
