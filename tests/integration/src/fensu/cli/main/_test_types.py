"""Test case types for CLI behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckCommandTestCase:
    """CLI check command inputs and expected process output."""

    description: str
    argv: tuple[str, ...]
    rule_code: str
    expected_exit_code: int
    expected_output_fragment: str
    expected_no_output_fragment: str


@dataclass(frozen=True)
class CheckNoFaultTestCase:
    """CLI check command inputs and expected no-fault output."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragment: str


@dataclass(frozen=True)
class WarningCheckTestCase:
    """Configured warning source and expected plain or advisory command behavior."""

    description: str
    source: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_summary: str
    expected_warning_count: int
    expected_fault_count: int


@dataclass(frozen=True)
class WarningCacheIdentityTestCase:
    """Alternating warning-mode invocations and expected cache operation counts."""

    description: str
    first_argv: tuple[str, ...]
    second_argv: tuple[str, ...]
    third_argv: tuple[str, ...]
    expected_switch_stats: str
    expected_warm_stats: str


@dataclass(frozen=True)
class ThresholdOverrideCheckTestCase:
    """Threshold override selection and expected cold/warm reporting."""

    description: str
    selected_rule: str
    override_value: int
    expected_output_fragment: str
    expected_additional_fragment: str
    expected_reason_fragment: str
    expected_absent_fragment: str
    expected_exit_code: int


@dataclass(frozen=True)
class NestedContainerCacheTestCase:
    """Nested container fault and expected cold/warm cache behavior."""

    description: str
    expected_exit_code: int
    expected_fault_fragment: str
    expected_summary_fragment: str
    expected_cold_stats_fragment: str
    expected_warm_stats_fragment: str
    expected_non_cacheable_fragment: str


@dataclass(frozen=True)
class CheckErrorTestCase:
    """CLI check input and expected configuration error output."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_error_fragment: str


@dataclass(frozen=True)
class MemoryCheckIntegrationTestCase:
    """Enabled memory source and expected combined architecture check response."""

    description: str
    expected_exit_code: int
    expected_memory_fault: str
    expected_architecture_summary: str
    expected_memory_summary: str


@dataclass(frozen=True)
class CustomRuleCoverageTestCase:
    """Configured custom rules and expected source-owned FFR707 diagnostics."""

    description: str
    test_source: str | None
    minimum: int
    use_rule_module: bool
    second_rule: bool
    expected_fault_count: int
    expected_output_fragment: str


@dataclass(frozen=True)
class CustomRuleCoverageCacheTestCase:
    """Expected source-owned cache behavior across test namespace mutations."""

    description: str
    expected_cold_stats: str
    expected_warm_stats: str
    expected_add_stats: str
    expected_remove_stats: str
    expected_fault_fragment: str


@dataclass(frozen=True)
class CustomRuleCoverageWarningTestCase:
    """Plain and warning-mode expectations for warn-only FFR707."""

    description: str
    expected_plain_summary: str
    expected_warning_summary: str
    expected_warning_fragment: str
    expected_plain_cold_stats: str
    expected_plain_warm_stats: str
    expected_warning_cold_stats: str
    expected_warning_warm_stats: str


@dataclass(frozen=True)
class EvaluationCheckTestCase:
    """Configured evaluation filter and expected cached/uncached CLI output."""

    description: str
    expected_exit_code: int
    expected_evaluation_footer: str
    expected_fault_fragment: str
    expected_absent_fragment: str


@dataclass(frozen=True)
class ParallelCheckTestCase:
    """One parallel mode and its expected serial-equivalent result."""

    description: str
    jobs: str
    cache_flag: str
    expected_exit_code: int
    expected_fault_fragments: tuple[str, ...]
    expected_cache_exists: bool
    expected_cache_stats_fragment: str
    expected_worker_partitions: int


@dataclass(frozen=True)
class CheckCacheModeTestCase:
    """Cached and uncached CLI modes with expected parity and storage behavior."""

    description: str
    cached_argv: tuple[str, ...]
    uncached_argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragment: str
    expected_cache_exists: bool


@dataclass(frozen=True)
class CheckCachePreferenceTestCase:
    """Configured cache preference, CLI override, and expected storage behavior."""

    description: str
    configured_enabled: bool
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_cache_exists: bool


@dataclass(frozen=True)
class CheckCacheWarningTestCase:
    """One cache failure mode and the expected diagnostic-stream warning."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragment: str
    expected_warning_fragment: str


@dataclass(frozen=True)
class ShortCircuitCheckTestCase:
    """One warm-run output short-circuit expectation."""

    description: str
    expected_exit_code: int
    expected_warm_restores: int
    expected_edited_restores: int
    expected_edited_fragment: str


@dataclass(frozen=True)
class ReplayFastPathTestCase:
    """One warm-run record-decode bypass expectation."""

    description: str
    expected_exit_code: int
    expected_warm_loads: int
    expected_edited_loads: int
    expected_warm_context_loads: int


@dataclass(frozen=True)
class ScopedCacheWarningTestCase:
    """One scoped warn-mode cache expectation for an uncacheable custom rule."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragment: str
    expected_cold_stats: str
    expected_warm_stats: str


@dataclass(frozen=True)
class MixedRulesetCacheTestCase:
    """One mixed cacheable/non-cacheable ruleset parity and purity expectation."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_custom_fragment: str
    expected_core_fragment: str
    expected_cold_stats: str
    expected_warm_stats: str


@dataclass(frozen=True)
class CacheableNoticeTestCase:
    """One custom-rule declaration state and the expected stderr notice."""

    description: str
    decorator_arguments: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_notice: bool
