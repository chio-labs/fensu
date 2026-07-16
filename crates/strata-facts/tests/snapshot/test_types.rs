//! Test-case types for snapshot walking and hashing behavior.

pub(crate) struct FixtureFile {
    pub(crate) path: &'static str,
    pub(crate) contents: &'static str,
}

pub(crate) struct FixtureSymlink {
    pub(crate) path: &'static str,
    pub(crate) target: &'static str,
}

pub(crate) struct WalkTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) symlinks: &'static [FixtureSymlink],
    pub(crate) expected_entries: &'static [ExpectedEntry],
}

pub(crate) struct ExpectedEntry {
    pub(crate) entry_suffix: &'static str,
    pub(crate) expected_parts: Option<&'static [&'static str]>,
}

pub(crate) struct CanonicalTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_canonical_suffix: &'static str,
}

pub(crate) struct HashTestCase {
    pub(crate) description: &'static str,
    pub(crate) contents: Option<&'static str>,
    pub(crate) expected_hash: Option<&'static str>,
}

pub(crate) struct GlobTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_direct_paths: &'static [&'static str],
    pub(crate) expected_recursive_paths: &'static [&'static str],
}

pub(crate) struct StatTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_answers: &'static [Option<(&'static str, bool)>],
}

pub(crate) struct ContextTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_source_hash: &'static str,
    pub(crate) expected_directory_entries: &'static [&'static str],
    pub(crate) expected_anchor: &'static str,
}
