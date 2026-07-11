"""Test case types for tests rules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SftRuleFile:
    """A file to write for a tests rule case."""

    description: str
    relative_path: str
    source: str
    expected_written: bool = True


@dataclass(frozen=True)
class SftRuleTestCase:
    """Tests rule source tree and expected fault facts."""

    description: str
    rule_code: str
    files: tuple[SftRuleFile, ...]
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
    runtime_paths: tuple[str, ...] = field(default_factory=tuple)
    tooling_paths: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SftOperationTestCase:
    """Expected operation counts from evaluating the complete SFT family."""

    description: str
    expected_parse_count: int
    expected_layout_count: int
