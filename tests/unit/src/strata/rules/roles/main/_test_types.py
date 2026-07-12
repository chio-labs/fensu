"""Test case types for roles rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from strata.discovery.types import ScopeName
from strata.rules.authoring.types import Threshold


@dataclass(frozen=True)
class SfrSupportFile:
    """An additional file used to construct a role layout."""

    description: str
    relative_path: str
    source: str
    expected_written: bool = True
    is_directory: bool = False


@dataclass(frozen=True)
class SfrRuleTestCase:
    """Roles rule source and expected fault facts."""

    description: str
    rule_code: str
    relative_path: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
    support_files: tuple[SfrSupportFile, ...] = field(default_factory=tuple)
    thresholds: dict[Threshold, int] = field(default_factory=dict)
    expected_messages: tuple[str, ...] = field(default_factory=tuple)
    expected_remediations: tuple[str, ...] = field(default_factory=tuple)
    expected_paths: tuple[str, ...] = field(default_factory=tuple)
    scope: ScopeName = ScopeName.ROOT
