"""Refuse automatic migration of invalid existing repository memory."""

from __future__ import annotations

from pathlib import Path

from strata.scaffolding.exceptions import InitError


def inspect_existing_memory(repository: Path) -> None:
    """Accept canonical existing memory or require manual migration before init."""

    from strata.memory.exceptions import MemoryError
    from strata.memory.main.inspect_memory_sources import inspect_memory_sources
    from strata.memory.models import MemoryIndexSummary

    try:
        summary: MemoryIndexSummary = inspect_memory_sources(repository)
    except MemoryError as error:
        raise InitError(f"Could not inspect existing .ai memory: {error}") from error
    diagnostics: int = (
        summary.source_diagnostic_count
        + summary.corpus_diagnostic_count
        + summary.graph_diagnostic_count
    )
    if diagnostics:
        raise InitError(
            "Existing .ai content is not canonical and will not be migrated automatically; "
            "migrate it manually before enabling memory."
        )
