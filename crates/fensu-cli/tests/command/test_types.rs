pub(crate) struct NativeMemoryCommandTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_output: &'static str,
}

pub(crate) struct InvalidMemoryArgumentsTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct CheckCleanupTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_exit_code: i32,
}

pub(crate) struct CheckPreservationTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_path: &'static str,
}

pub(crate) struct CheckCacheTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_cold_fragment: &'static str,
    pub(crate) expected_warm_fragment: &'static str,
}

pub(crate) struct CheckPolicyTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_present: &'static str,
    pub(crate) expected_absent: &'static str,
}

pub(crate) struct InvalidCheckConfigTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct RuleOptionsCheckRoutingTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_stdout: &'static str,
    pub(crate) expected_stderr: &'static str,
}

pub(crate) struct RuleRemediationTestCase {
    pub(crate) description: &'static str,
    pub(crate) code: &'static str,
    pub(crate) expected_fragment: &'static str,
}

pub(crate) struct PreExecutionCleanupTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_path: &'static str,
}
