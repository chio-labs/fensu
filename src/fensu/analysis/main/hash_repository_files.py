"""Hash repository files through one optional native batch."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME


def hash_repository_files(*, paths: tuple[Path, ...]) -> tuple[str | None, ...]:
    """Return native content hashes in path order or misses for safe fallback."""

    unavailable: tuple[None, ...] = (None,) * len(paths)
    if not paths:
        return unavailable
    try:
        fensu_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
        hashes: list[str | None] = fensu_facts.hash_source_files(list(paths))
    except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
        return unavailable
    return tuple(hashes) if len(hashes) == len(paths) else unavailable
