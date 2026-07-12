"""Test case types for CLI behavior."""

from __future__ import annotations

from dataclasses import dataclass

from strata.agentdocs.constants import GENERATED_MARKER


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
class ThresholdOverrideCheckTestCase:
    """Threshold override selection and expected cold/warm reporting."""

    description: str
    selected_rule: str
    override_value: int
    expected_output_fragment: str
    expected_additional_fragment: str
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
class MetadataCommandTestCase:
    """CLI metadata command inputs and expected output."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragments: tuple[str, ...]


@dataclass(frozen=True)
class RulePresentationTestCase:
    """Rule terminal styling inputs and expected output."""

    description: str
    argv: tuple[str, ...]
    is_terminal: bool
    no_color: bool
    expected_output_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...]


@dataclass(frozen=True)
class SkillCommandTestCase:
    """Skills update inputs and expected installed guidance."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragments: tuple[str, ...]
    expected_written_paths: tuple[str, ...] = ()
    expected_file_fragments: tuple[str, ...] = ()
    expected_absent_fragments: tuple[str, ...] = ()
    expected_file_fragment: str = GENERATED_MARKER


@dataclass(frozen=True)
class SkillTransactionFailureTestCase:
    """Failed replacement position and expected atomic update result."""

    description: str
    failure_at: int
    expected_exit_code: int
    expected_error_fragment: str


@dataclass(frozen=True)
class MapCommandTestCase:
    """Map command inputs and expected deterministic output."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragments: tuple[str, ...]


@dataclass(frozen=True)
class MethodMapTestCase:
    """Method map selector and expected presence or absence contracts."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...] = ()


@dataclass(frozen=True)
class StandaloneMapTestCase:
    """Map behavior for a repository without Strata configuration."""

    description: str
    configured_root: str
    argv: tuple[str, ...]
    relative_imports: bool
    expected_output_fragments: tuple[str, ...]


@dataclass(frozen=True)
class MapPresentationTestCase:
    """Map rendering options and their visible output contract."""

    description: str
    argv: tuple[str, ...]
    is_terminal: bool
    no_color: bool
    expected_output_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...]
    cycle: bool = False
    dynamic_seam: bool = False


@dataclass(frozen=True)
class InitInteractiveTestCase:
    """Interactive init script and expected layout/tooling result."""

    description: str
    package_paths: tuple[str, ...]
    tooling_paths: tuple[str, ...]
    scripted_input: str
    expected_roots: tuple[str, ...]
    expected_tests: tuple[str, ...]
    expected_tooling: tuple[str, ...]
    expected_output_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...] = ()


@dataclass(frozen=True)
class InitExecutionTestCase:
    """Non-interactive init inputs and expected files, config, and transcript."""

    description: str
    argv: tuple[str, ...]
    existing_project: bool
    stdin_isatty: bool
    stdout_isatty: bool
    expected_exit_code: int
    expected_config: str | None
    expected_output_fragments: tuple[str, ...]
    expected_error_fragment: str = ""
    expected_created_paths: tuple[str, ...] = ()
    expected_absent_fragments: tuple[str, ...] = ()


@dataclass(frozen=True)
class InitSelectionTestCase:
    """Multiple-root prompt input and expected selected config roots."""

    description: str
    scripted_input: str
    expected_exit_code: int
    expected_roots: tuple[str, ...] | None
    expected_output_fragments: tuple[str, ...]
    expected_error_fragment: str = ""


@dataclass(frozen=True)
class InitOptionTestCase:
    """Explicit init options and expected rendered config values."""

    description: str
    argv: tuple[str, ...]
    expected_roots: tuple[str, ...]
    expected_tests: tuple[str, ...]
    expected_tooling: tuple[str, ...]
    expected_select: tuple[str, ...]
    expected_skill_paths: tuple[str, ...]


@dataclass(frozen=True)
class InitRefusalTestCase:
    """Refusal source or response and expected no-write behavior."""

    description: str
    source: str
    scripted_input: str
    expected_error_fragment: str
    argv: tuple[str, ...] = ()
    expected_exit_code: int = 2
    expected_stdout_fragment: str = ""


@dataclass(frozen=True)
class InitRerunTestCase:
    """Local config source and flags with expected idempotent success output."""

    description: str
    source: str
    argv: tuple[str, ...]
    expected_relative_config: str
    expected_exit_code: int


@dataclass(frozen=True)
class InitPresentationTestCase:
    """Terminal color controls and expected semantic transcript fragments."""

    description: str
    is_terminal: bool
    no_color: bool
    include_fault: bool
    expected_output_fragments: tuple[str, ...]
    expected_absent_fragments: tuple[str, ...]


@dataclass(frozen=True)
class InitRoundTripTestCase:
    """Rendered init plan and expected validated project layout."""

    description: str
    expected_roots: tuple[str, ...]
    expected_tests: tuple[str, ...]
    expected_tooling: tuple[str, ...]
    expected_select: tuple[str, ...]


@dataclass(frozen=True)
class InitTranscriptTestCase:
    """Representative init invocation and its complete plain transcript."""

    description: str
    existing_project: bool
    argv: tuple[str, ...]
    scripted_input: str
    expected_transcript: str


@dataclass(frozen=True)
class InitApplicabilityTestCase:
    """Repository state, inapplicable options, and expected preflight refusal."""

    description: str
    existing_project: bool
    argv: tuple[str, ...]
    expected_error_fragment: str


@dataclass(frozen=True)
class InitDriftWarningTestCase:
    """Post-write drift failure and expected successful continuation output."""

    description: str
    scripted_input: str
    expected_exit_code: int
    expected_output_fragments: tuple[str, ...]
    expected_warning_fragment: str


@dataclass(frozen=True)
class InitSymlinkRefusalTestCase:
    """Unsafe local config symlink and expected no-write refusal behavior."""

    description: str
    expected_exit_code: int
    expected_error_fragment: str
    expected_stdout: str


@dataclass(frozen=True)
class InitLocalTargetTestCase:
    """Unsafe local config target and expected early refusal."""

    description: str
    target_kind: str
    expected_error_fragment: str
    expected_exit_code: int


@dataclass(frozen=True)
class InitPromptFailureTestCase:
    """Scripted prompt failure and expected command-level preservation behavior."""

    description: str
    scripted_input: str
    expected_exit_code: int
    expected_error_fragment: str
    expected_config_written: bool
    expected_output_fragment: str
    expected_absent_fragment: str = "Traceback"
