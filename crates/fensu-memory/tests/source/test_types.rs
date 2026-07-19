//! Test-case and fixture types for canonical source discovery.

use fensu_memory::source::types::{DiagnosticKind, GitTracking};

pub(crate) struct FixtureFile {
    pub(crate) path: &'static str,
    pub(crate) contents: &'static str,
}

pub(crate) struct FixtureDirectory {
    pub(crate) path: &'static str,
}

pub(crate) struct FixtureSymlink {
    pub(crate) path: &'static str,
    pub(crate) target: &'static str,
}

pub(crate) struct ExpectedDiagnostic {
    pub(crate) path: &'static str,
    pub(crate) kind: DiagnosticKind,
}

pub(crate) struct CanonicalDiscoveryTestCase {
    pub(crate) description: &'static str,
    pub(crate) directories: &'static [FixtureDirectory],
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_document_paths: &'static [&'static str],
    pub(crate) expected_skill_file_paths: &'static [&'static str],
    pub(crate) expected_content_hash: &'static str,
    pub(crate) expected_byte_size: u64,
    pub(crate) expected_mtime_after_epoch: bool,
    pub(crate) expected_change_time: bool,
    pub(crate) expected_archived_document_count: usize,
    pub(crate) expected_archived_skill_file_count: usize,
}

pub(crate) struct DiagnosticDiscoveryTestCase {
    pub(crate) description: &'static str,
    pub(crate) directories: &'static [FixtureDirectory],
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_document_count: usize,
    pub(crate) expected_diagnostics: &'static [ExpectedDiagnostic],
}

pub(crate) struct CollisionDiscoveryTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_document_paths: &'static [&'static str],
    pub(crate) expected_skill_file_paths: &'static [&'static str],
    pub(crate) expected_diagnostics: &'static [ExpectedDiagnostic],
}

pub(crate) struct SymlinkDiscoveryTestCase {
    pub(crate) description: &'static str,
    pub(crate) directories: &'static [FixtureDirectory],
    pub(crate) files: &'static [FixtureFile],
    pub(crate) symlinks: &'static [FixtureSymlink],
    pub(crate) expected_document_count: usize,
    pub(crate) expected_diagnostics: &'static [ExpectedDiagnostic],
}

pub(crate) struct GitTrackingTestCase {
    pub(crate) description: &'static str,
    pub(crate) basename: &'static str,
    pub(crate) expected_tracking: GitTracking,
}

pub(crate) struct GitWorktreeTestCase {
    pub(crate) description: &'static str,
    pub(crate) basename: &'static str,
    pub(crate) expected_document_count: usize,
    pub(crate) expected_tracking: GitTracking,
}
