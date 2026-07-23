//! Deserialized native core-rule contract records.

use std::collections::HashMap;

use fensu_native::rules::models::NativeFaultRow;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub(crate) struct CoreRuleFixture {
    pub(crate) description: String,
    pub(crate) source: String,
    pub(crate) codes: Vec<String>,
    pub(crate) context: RuleContextFixture,
    pub(crate) project_files: Vec<ProjectFileFixture>,
    pub(crate) filesystem: Vec<FilesystemEntry>,
    pub(crate) entrypoint_modules: Vec<String>,
    #[serde(rename = "expected")]
    pub(crate) expected_faults: Vec<ExpectedFault>,
}

pub(crate) struct CoreRuleCorpusTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_fixture_count: usize,
}

pub(crate) struct NativeOptionRejectionTestCase {
    pub(crate) description: &'static str,
    pub(crate) code: &'static str,
    pub(crate) option_name: &'static str,
    pub(crate) option_value: &'static str,
    pub(crate) expected_error_fragment: &'static str,
    pub(crate) expected_stored_value: &'static str,
}

#[derive(Debug, Deserialize)]
pub(crate) struct FilesystemEntry {
    pub(crate) path: String,
    pub(crate) content: Option<String>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct RuleContextFixture {
    pub(crate) scope: String,
    pub(crate) role: Option<String>,
    pub(crate) is_main_module: bool,
    pub(crate) thresholds: HashMap<String, u32>,
    pub(crate) repository_path: String,
    pub(crate) contracts: Vec<(String, String)>,
    pub(crate) relative_parts: Vec<String>,
    pub(crate) is_entry_module: bool,
    pub(crate) package_name: String,
    pub(crate) tooling_packages: Vec<String>,
    pub(crate) scope_roots: Vec<(String, String)>,
    pub(crate) observations: HashMap<String, Vec<String>>,
    pub(crate) custom_registrations: Vec<(String, String, String, String, u32, u32)>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct ProjectFileFixture {
    pub(crate) path: String,
    pub(crate) scope: String,
    pub(crate) module_parts: Vec<String>,
    pub(crate) source: String,
}

#[derive(Debug, Deserialize, Eq, PartialEq)]
pub(crate) struct ExpectedFault {
    pub(crate) code: String,
    pub(crate) path: Option<String>,
    pub(crate) line: Option<u32>,
    pub(crate) column: Option<u32>,
    pub(crate) message: Option<String>,
    pub(crate) remediation: Option<String>,
}

impl From<NativeFaultRow> for ExpectedFault {
    fn from(row: NativeFaultRow) -> Self {
        let location = (row.line != 0).then_some((row.line, row.column));
        Self {
            code: row.code,
            path: row.path,
            line: location.map(|(line, _)| line),
            column: location.map(|(_, column)| column),
            message: row.message,
            remediation: row.remediation,
        }
    }
}
