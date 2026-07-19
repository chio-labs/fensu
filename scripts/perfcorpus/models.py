"""Structured inputs and outputs for corpus generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from scripts.perfcorpus.constants import (
    DEFAULT_ANNOTATION_FAULT_EVERY,
    DEFAULT_MAGIC_FAULT_EVERY,
)


@dataclass(frozen=True, slots=True)
class CorpusSpec:
    """One deterministic corpus generation request."""

    target: Path
    file_target: int
    seed: int
    annotation_fault_every: int = DEFAULT_ANNOTATION_FAULT_EVERY
    magic_fault_every: int = DEFAULT_MAGIC_FAULT_EVERY


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
