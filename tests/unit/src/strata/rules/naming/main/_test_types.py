"""Test case types for naming rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from strata.config.exceptions import ConfigError


@dataclass(frozen=True)
class SfnRuleTestCase:
    """Naming rule source and expected fault facts."""

    description: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
    contracts: dict[str, str] = field(default_factory=dict)
    expected_message_fragments: tuple[str, ...] = ()
    expected_remediation_fragments: tuple[str, ...] = ()


@dataclass(frozen=True)
class SfnConflictTestCase:
    """Overlapping contracts and their deterministic configuration error."""

    description: str
    source: str
    contracts: dict[str, str]
    expected_error_type: type[ConfigError]
    expected_message: str
