//! Test-case and fixture types for corpus loading.

use strata_memory::corpus::types::CorpusDiagnosticKind;

pub(crate) struct FixtureFile {
    pub(crate) path: &'static str,
    pub(crate) contents: &'static [u8],
}

pub(crate) struct ExpectedCorpusDiagnostic {
    pub(crate) path: &'static str,
    pub(crate) kind: CorpusDiagnosticKind,
}

pub(crate) struct MixedCorpusTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_document_paths: &'static [&'static str],
    pub(crate) expected_titles: &'static [Option<&'static str>],
    pub(crate) expected_diagnostics: &'static [ExpectedCorpusDiagnostic],
}

pub(crate) struct TitleValidationTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_titles: &'static [Option<&'static str>],
    pub(crate) expected_diagnostics: &'static [ExpectedCorpusDiagnostic],
}

pub(crate) struct OrderingTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_document_paths: &'static [&'static str],
    pub(crate) expected_skill_file_paths: &'static [&'static str],
    pub(crate) expected_source_diagnostic_paths: &'static [&'static str],
    pub(crate) expected_diagnostics: &'static [ExpectedCorpusDiagnostic],
}
