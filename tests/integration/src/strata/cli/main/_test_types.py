"""Test case types for CLI behavior."""

from __future__ import annotations

from dataclasses import dataclass

from strata.agentdocs.core.constants import GENERATED_MARKER


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
    expected_absent_fragments: tuple[str, ...] = ()
    expected_file_fragment: str = GENERATED_MARKER


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
