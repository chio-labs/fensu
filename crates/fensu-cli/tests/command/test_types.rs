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

pub(crate) struct SymbolExceptionTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_applied: &'static str,
    pub(crate) expected_retained_location: &'static str,
    pub(crate) expected_suppressed_location: &'static str,
}

pub(crate) struct ColoredCheckTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_fragment: &'static str,
}

pub(crate) struct InvalidCheckConfigTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct TargetCheckTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_stdout: &'static str,
    pub(crate) expected_stderr: &'static str,
}

pub(crate) struct ProjectAwareTargetTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_present: &'static str,
    pub(crate) expected_absent: &'static str,
    pub(crate) expected_cleared: &'static str,
}

pub(crate) struct CanonicalAliasDiagnosticTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_present: &'static str,
    pub(crate) expected_alias_absent: &'static str,
    pub(crate) expected_double_prefix_absent: &'static str,
}

pub(crate) struct TargetCacheCheckTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_lenient_exit_code: i32,
    pub(crate) expected_strict_exit_code: i32,
    pub(crate) expected_strict_stdout: &'static str,
    pub(crate) expected_lenient_absent: &'static str,
}

pub(crate) struct TargetCleanupTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_removed_path: &'static str,
    pub(crate) expected_preserved_path: &'static str,
}

pub(crate) struct ConfigCommandTargetTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_stdout: &'static str,
    pub(crate) expected_stderr: &'static str,
}

pub(crate) struct TargetSkillFreshnessTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_stderr: &'static str,
}

pub(crate) struct ConfigDiscoveryTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
}

pub(crate) struct ThresholdPrecedenceTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_present: &'static str,
    pub(crate) expected_absent: &'static str,
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

pub(crate) struct RuleColorTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_fragment: &'static str,
}

pub(crate) struct NativeRulePackTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_output: &'static str,
}

pub(crate) struct RulePackLookupTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_fragments: &'static [&'static str],
}

pub(crate) struct EffectiveRulePolicyTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) expected_fragments: &'static [&'static str],
}

pub(crate) struct OwnerPlanningTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_fault_count: usize,
}

pub(crate) struct PreExecutionCleanupTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_path: &'static str,
}
