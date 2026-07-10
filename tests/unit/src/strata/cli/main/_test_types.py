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
    """Skill command inputs and expected generated guidance."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragments: tuple[str, ...]


@dataclass(frozen=True)
class MapCommandTestCase:
    """Map command inputs and expected deterministic output."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragments: tuple[str, ...]


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
class EntryDispatchTestCase:
    """CLI argv and expected delegated command runner."""

    description: str
    argv: tuple[str, ...]
    runner_attribute: str
    expected_forwarded_argv: tuple[str, ...]
    expected_exit_code: int
