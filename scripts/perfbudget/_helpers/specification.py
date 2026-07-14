"""Resolve one complete budget specification from command-line inputs."""

from __future__ import annotations

import sys
from importlib.util import find_spec
from pathlib import Path

from scripts.perfbudget.constants import (
    DEFAULT_COLD_CEILING_SECONDS,
    DEFAULT_EDIT_CEILING_SECONDS,
    DEFAULT_NATIVE_COLD_CEILING_SECONDS,
    DEFAULT_NATIVE_EDIT_CEILING_SECONDS,
    DEFAULT_NATIVE_UNCACHED_CEILING_SECONDS,
    DEFAULT_NATIVE_WARM_CEILING_SECONDS,
    DEFAULT_UNCACHED_CEILING_SECONDS,
    DEFAULT_WARM_CEILING_SECONDS,
)
from scripts.perfbudget.models import BudgetSpec
from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.types import FactBackend


def resolved_budget_spec(
    *,
    backend: str,
    files: int,
    seed: int,
    uncached_ceiling: float | None,
    cold_ceiling: float | None,
    warm_ceiling: float | None,
    edit_ceiling: float | None,
    executable: Path | None,
) -> BudgetSpec:
    """Build one budget specification with backend-appropriate default ceilings."""

    native: bool = backend == FactBackend.NATIVE
    default_uncached: float = (
        DEFAULT_NATIVE_UNCACHED_CEILING_SECONDS if native else DEFAULT_UNCACHED_CEILING_SECONDS
    )
    default_cold: float = (
        DEFAULT_NATIVE_COLD_CEILING_SECONDS if native else DEFAULT_COLD_CEILING_SECONDS
    )
    default_warm: float = (
        DEFAULT_NATIVE_WARM_CEILING_SECONDS if native else DEFAULT_WARM_CEILING_SECONDS
    )
    default_edit: float = (
        DEFAULT_NATIVE_EDIT_CEILING_SECONDS if native else DEFAULT_EDIT_CEILING_SECONDS
    )
    return BudgetSpec(
        executable=executable if executable is not None else _default_executable(),
        backend=backend,
        file_target=files,
        seed=seed,
        uncached_ceiling=uncached_ceiling if uncached_ceiling is not None else default_uncached,
        cold_ceiling=cold_ceiling if cold_ceiling is not None else default_cold,
        warm_ceiling=warm_ceiling if warm_ceiling is not None else default_warm,
        edit_ceiling=edit_ceiling if edit_ceiling is not None else default_edit,
    )


def is_native_backend_available() -> bool:
    """Report whether the native fact extension is importable in this environment."""

    return find_spec(NATIVE_FACT_MODULE_NAME) is not None


def _default_executable() -> Path:
    return Path(sys.executable).parent / "strata"
