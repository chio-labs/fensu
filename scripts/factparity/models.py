"""Result models for fact-backend parity checking."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FamilyDiff:
    """One fact family whose backends disagreed for one file."""

    path: Path
    family: str
    expected: str
    actual: str


@dataclass(frozen=True, slots=True)
class ParityReport:
    """The aggregate outcome of one parity run."""

    checked_file_count: int
    skipped_file_count: int
    diffs: tuple[FamilyDiff, ...]
