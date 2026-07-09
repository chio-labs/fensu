"""Test case types for rule authoring (decorator and class styles)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.rules.authoring.types import Family, RuleKind


@dataclass(frozen=True)
class FaultFormatTestCase:
    """A Fault rendered against a repo root into a text line."""

    description: str
    code: str
    path: Path
    message: str
    line: int | None
    column: int | None
    root: Path
    expected_rendered: str


@dataclass(frozen=True)
class EnumMembersTestCase:
    """An enum's actual and expected member-name-to-value mapping."""

    description: str
    actual_members: dict[str, str]
    expected_members: dict[str, str]


@dataclass(frozen=True)
class RuleEnvelopeTestCase:
    """A set of envelope arguments and the rule identity they should produce."""

    description: str
    code: str
    family: Family | str
    slug: str
    message: str
    expected_code: str
    expected_family: Family
    expected_kind: RuleKind


@dataclass(frozen=True)
class InvalidEnvelopeTestCase:
    """A set of envelope arguments that should be rejected at definition time."""

    description: str
    code: str
    family: Family | str
    slug: str
    message: str
    expected_error_fragment: str


@dataclass(frozen=True)
class ModuleMetadataTestCase:
    """A module metadata discovery scenario and expected rule codes."""

    description: str
    expected_codes: tuple[str, ...]
