pub(crate) struct DetectionTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) files: Vec<(&'static str, String)>,
    pub(crate) expected_links: &'static [(&'static str, &'static str, &'static str)],
    pub(crate) expected_absent: &'static [&'static str],
}

pub(crate) struct CommandOutputTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: String,
    pub(crate) files: Vec<(&'static str, String)>,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_stdout: &'static [&'static str],
    pub(crate) expected_stderr: &'static [&'static str],
}

pub(crate) struct ClusterTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: String,
    pub(crate) files: Vec<(&'static str, String)>,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_clusters: Vec<Vec<&'static str>>,
    pub(crate) expected_allowlisted_pairs: u64,
    pub(crate) expected_contract_exempt_members: u64,
}

pub(crate) struct ChangedSinceTestCase {
    pub(crate) description: &'static str,
    pub(crate) committed: Vec<(&'static str, String)>,
    pub(crate) removed: &'static [&'static str],
    pub(crate) staged: Vec<(&'static str, String)>,
    pub(crate) worktree: Vec<(&'static str, String)>,
    pub(crate) expected_clusters: Vec<Vec<&'static str>>,
}

pub(crate) struct JsonShapeTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_report_keys: &'static [&'static str],
    pub(crate) expected_cluster_keys: &'static [&'static str],
    pub(crate) expected_member_keys: &'static [&'static str],
    pub(crate) expected_diff_lines: &'static [(u64, u64, &'static str)],
}
