"""Structured inputs and outputs for corpus generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class CorpusSpec:
    """One deterministic corpus generation request."""

    target: Path
    file_target: int
    seed: int


@dataclass(frozen=True, slots=True)
class CorpusSummary:
    """Deterministic result of one corpus generation."""

    files_written: int
    domains: int
    faults_expected: int


@dataclass(frozen=True, slots=True)
class RenderedFiles:
    """Rendered relative paths, contents, and expected fault count."""

    files: MappingProxyType[str, str]
    faults: int
