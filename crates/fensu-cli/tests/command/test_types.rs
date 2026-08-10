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

pub(crate) struct WebThresholdCacheIdentityTestCase {
    pub(crate) description: &'static str,
    pub(crate) alias: &'static str,
    pub(crate) canonical: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_cold: &'static str,
    pub(crate) expected_warm: &'static str,
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

pub(crate) struct WebCacheCheckTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_cold: &'static str,
    pub(crate) expected_warm: &'static str,
    pub(crate) expected_invalidated: &'static str,
}

pub(crate) struct WebParseDiagnosticTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_svelte: &'static str,
    pub(crate) expected_typescript: &'static str,
}

pub(crate) struct WebSourcePurposeTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) files: &'static [(&'static str, &'static str)],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_present: Option<&'static str>,
    pub(crate) expected_absent: Option<&'static str>,
}

pub(crate) struct WebTestCaseTypeResolutionTestCase {
    pub(crate) description: &'static str,
    pub(crate) test_source: &'static str,
    pub(crate) support_source: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_fwt403: bool,
}

pub(crate) struct WebExceptionOwnerTestCase {
    pub(crate) description: &'static str,
    pub(crate) symbol: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_stdout: &'static str,
    pub(crate) expected_stderr: &'static str,
}

pub(crate) struct InternalGateCommandTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_error: &'static str,
}

pub(crate) struct WebConfigFailureTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [(&'static str, &'static str)],
    pub(crate) expected_error: &'static str,
}

pub(crate) struct CacheBoundTestCase {
    pub(crate) description: &'static str,
    pub(crate) generation_count: usize,
    pub(crate) expected_namespace_count: i64,
    pub(crate) expected_record_count: i64,
}

pub(crate) struct HostedWebPolicyTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct WebPolicyCheckTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
}

pub(crate) struct WebDiagnosticCountTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: &'static str,
    pub(crate) files: &'static [(&'static str, &'static str)],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_counts: &'static [(&'static str, usize)],
    pub(crate) expected_absent: Option<&'static str>,
}

pub(crate) struct MixedWebExecutionTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_python_fault: &'static str,
    pub(crate) expected_web_fault: &'static str,
    pub(crate) expected_host_count_per_run: usize,
    pub(crate) expected_host_error: &'static str,
}
