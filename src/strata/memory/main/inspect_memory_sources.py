"""Inspect canonical memory sources without configuration or publication."""

from __future__ import annotations

from pathlib import Path

from strata.memory._helpers.native_operations import inspect_sources
from strata.memory.models import MemoryIndexSummary


def inspect_memory_sources(repository_root: Path) -> MemoryIndexSummary:
    """Return source, corpus, and graph diagnostics without writing SQLite."""

    return inspect_sources(repository_root)
