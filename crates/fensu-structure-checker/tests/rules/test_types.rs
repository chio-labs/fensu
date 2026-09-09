//! Test-case types for structure checker tests.

use fensu_structure_checker::models::CheckerConfig;

pub(crate) struct RepoFile {
    pub(crate) path: String,
    pub(crate) contents: String,
}

pub(crate) struct CheckRepoTestCase {
    pub(crate) description: &'static str,
    pub(crate) repo_files: Vec<RepoFile>,
    pub(crate) expected_violation_codes: Vec<&'static str>,
}

pub(crate) struct ParserConfigTestCase {
    pub(crate) description: &'static str,
    pub(crate) repo_files: Vec<RepoFile>,
    pub(crate) config: CheckerConfig,
    pub(crate) expected_violation_count: usize,
    pub(crate) expected_remediation: &'static str,
}

pub(crate) struct ToolingConfigTestCase {
    pub(crate) description: &'static str,
    pub(crate) repo_files: Vec<RepoFile>,
    pub(crate) config: CheckerConfig,
    pub(crate) expected_code: &'static str,
    pub(crate) expected_message: &'static str,
    pub(crate) expected_present: bool,
}

pub(crate) struct ConfigValidationTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: CheckerConfig,
    pub(crate) expected_is_error: bool,
}

pub(crate) struct RepositoryPolicyTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_present_code: &'static str,
    pub(crate) expected_absent_codes: Vec<&'static str>,
}
