//! Test-case types for structure checker tests.

pub(crate) struct RepoFile {
    pub(crate) path: String,
    pub(crate) contents: String,
}

pub(crate) struct CheckRepoTestCase {
    pub(crate) description: &'static str,
    pub(crate) repo_files: Vec<RepoFile>,
    pub(crate) expected_violation_codes: Vec<&'static str>,
}
