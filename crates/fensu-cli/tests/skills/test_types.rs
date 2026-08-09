use std::path::Path;

pub(crate) struct SkillsCommandTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
}

pub(crate) struct InvalidSkillsConfigTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct FreshnessTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_state: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_update_exit_code: i32,
    pub(crate) mutate: fn(&Path, &Path, &[u8]),
}

pub(crate) struct ExceptionSymbolTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static [u8],
    pub(crate) symbol: &'static str,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct PublicationRaceTestCase {
    pub(crate) description: &'static str,
    pub(crate) staged_payload_size: usize,
    pub(crate) expected_exit_code: i32,
}

pub(crate) struct RepositoryGuidanceTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_fragments: &'static [&'static str],
    pub(crate) unexpected_fragments: &'static [&'static str],
}
