"""Seed snapshot content hashes for target files through the native backend."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend
from strata.discovery.constants import SNAPSHOT_TABLE


def prime_snapshot_hashes(*, paths: tuple[Path, ...]) -> None:
    """Hash every path natively in one batch and seed the snapshot table."""

    if select_fact_backend().backend is not FactBackend.NATIVE or not paths:
        return
    try:
        strata_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    except ImportError:
        return
    hashes: list[str | None] = strata_facts.hash_source_files(list(paths))
    hash_by_path: dict[str, str] = {}
    for path, digest in zip(paths, hashes, strict=True):
        if digest is not None:
            hash_by_path[str(path)] = digest
    SNAPSHOT_TABLE.seed_hashes(hash_by_path=hash_by_path)
