"""Hash repository files through one optional native batch."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend


def hash_repository_files(*, paths: tuple[Path, ...]) -> tuple[str | None, ...]:
    """Return native content hashes in path order or misses for safe fallback."""

    unavailable: tuple[None, ...] = (None,) * len(paths)
    if select_fact_backend().backend is not FactBackend.NATIVE or not paths:
        return unavailable
    try:
        strata_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
        hashes: list[str | None] = strata_facts.hash_source_files(list(paths))
    except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
        return unavailable
    return tuple(hashes) if len(hashes) == len(paths) else unavailable
