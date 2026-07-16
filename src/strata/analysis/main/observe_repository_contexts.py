"""Observe repository source and namespace state through one optional native batch."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME, REPOSITORY_CONTEXT_ROW_LENGTH
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.models import RepositoryContextAnswer
from strata.analysis.types import FactBackend, ProjectDependencyKind


def observe_repository_contexts(
    *,
    repo_root: Path,
    queries: tuple[tuple[str, ProjectDependencyKind], ...],
) -> tuple[RepositoryContextAnswer | None, ...]:
    """Return native source and namespace answers or misses for safe fallback."""

    unavailable: tuple[None, ...] = (None,) * len(queries)
    if select_fact_backend().backend is not FactBackend.NATIVE or not queries:
        return unavailable
    try:
        strata_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
        rows: list[tuple[str, str | None, list[str]] | None] = (
            strata_facts.observe_repository_contexts(
                repo_root,
                [(path, kind.value) for path, kind in queries],
            )
        )
    except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
        return unavailable
    if len(rows) != len(queries):
        return unavailable
    answers: list[RepositoryContextAnswer | None] = []
    for query, row in zip(queries, rows, strict=True):
        if not _context_row_is_valid(query=query, row=row):
            answers.append(None)
            continue
        if row is None:
            answers.append(None)
            continue
        answer: None | str | tuple[str, ...] = (
            row[1] if query[1] is ProjectDependencyKind.SOURCE else tuple(row[2])
        )
        answers.append(RepositoryContextAnswer(dependency_path=row[0], answer=answer))
    return tuple(answers)


def _context_row_is_valid(
    *,
    query: tuple[str, ProjectDependencyKind],
    row: tuple[str, str | None, list[str]] | None,
) -> bool:
    if row is None:
        return True
    if (
        not isinstance(row, tuple)
        or len(row) != REPOSITORY_CONTEXT_ROW_LENGTH
        or not isinstance(row[0], str)
        or not (row[1] is None or isinstance(row[1], str))
        or not isinstance(row[2], list)
        or not all(isinstance(path, str) for path in row[2])
    ):
        return False
    if query[1] is ProjectDependencyKind.SOURCE:
        return not row[2]
    return row[1] is None
