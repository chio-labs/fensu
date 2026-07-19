//! Type-layer declarations for the structure checker.

/// The structural role a checked file plays inside its crate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FileKind {
    LibraryRoot,
    BinAdapter,
    ModRoot,
    ModuleFile,
    TestHarness,
    TestTypes,
    TestHelpers,
    TestTopic,
}
