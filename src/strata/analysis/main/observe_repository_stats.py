"""Observe live repository metadata through one optional native batch."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME, REPOSITORY_QUERY_ROW_LENGTH
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.models import RepositoryStatAnswer
from strata.analysis.types import FactBackend, ProjectDependencyKind


def observe_repository_stats(
    *,
    repo_root: Path,
    queries: tuple[tuple[str, ProjectDependencyKind], ...],
) -> tuple[RepositoryStatAnswer | None, ...]:
    """Return native stat answers in query order or misses for safe fallback."""

    unavailable: tuple[None, ...] = (None,) * len(queries)
    if select_fact_backend().backend is not FactBackend.NATIVE or not queries:
        return unavailable
    try:
        strata_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
        rows: list[tuple[str, bool] | None] = strata_facts.observe_repository_stats(
            repo_root,
            [(path, kind.value) for path, kind in queries],
        )
    except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
        return unavailable
    if len(rows) != len(queries):
        return unavailable
    answers: list[RepositoryStatAnswer | None] = []
    for row in rows:
        if (
            row is None
            or not isinstance(row, tuple)
            or len(row) != REPOSITORY_QUERY_ROW_LENGTH
            or not isinstance(row[0], str)
            or not isinstance(row[1], bool)
        ):
            answers.append(None)
            continue
        answers.append(RepositoryStatAnswer(dependency_path=row[0], answer=row[1]))
    return tuple(answers)
