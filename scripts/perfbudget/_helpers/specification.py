"""Resolve one complete budget specification from command-line inputs."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.perfbudget.constants import (
    DEFAULT_COLD_CEILING_SECONDS,
    DEFAULT_EDIT_CEILING_SECONDS,
    DEFAULT_INIT_CEILING_SECONDS,
    DEFAULT_UNCACHED_CEILING_SECONDS,
    DEFAULT_VERSION_CEILING_SECONDS,
    DEFAULT_WARM_CEILING_SECONDS,
)
from scripts.perfbudget.models import BudgetSpec


def resolved_budget_spec(
    *,
    files: int,
    seed: int,
    uncached_ceiling: float | None,
    cold_ceiling: float | None,
    warm_ceiling: float | None,
    edit_ceiling: float | None,
    version_ceiling: float | None,
    init_ceiling: float | None,
    executable: Path | None,
) -> BudgetSpec:
    """Build one native budget specification with explicit ceiling overrides."""

    return BudgetSpec(
        executable=executable if executable is not None else _default_executable(),
        file_target=files,
        seed=seed,
        uncached_ceiling=(
            uncached_ceiling if uncached_ceiling is not None else DEFAULT_UNCACHED_CEILING_SECONDS
        ),
        cold_ceiling=(cold_ceiling if cold_ceiling is not None else DEFAULT_COLD_CEILING_SECONDS),
        warm_ceiling=(warm_ceiling if warm_ceiling is not None else DEFAULT_WARM_CEILING_SECONDS),
        edit_ceiling=(edit_ceiling if edit_ceiling is not None else DEFAULT_EDIT_CEILING_SECONDS),
        version_ceiling=(
            version_ceiling if version_ceiling is not None else DEFAULT_VERSION_CEILING_SECONDS
        ),
        init_ceiling=(init_ceiling if init_ceiling is not None else DEFAULT_INIT_CEILING_SECONDS),
    )


def _default_executable() -> Path:
    return Path(sys.executable).parent / "strata"
