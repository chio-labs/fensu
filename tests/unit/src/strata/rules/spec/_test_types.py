"""Test case types for the rule-definition vocabulary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
