"""Local helpers for budget scenario tests."""

from __future__ import annotations

from scripts.perfbudget.main.run_budget import run_budget


def uniform_budget_run(*, file_target: int, seed: int, ceiling_seconds: float) -> int:
    """Run every scenario with one shared ceiling and return the exit code."""

    return run_budget(
        files=file_target,
        seed=seed,
        uncached_ceiling=ceiling_seconds,
        cold_ceiling=ceiling_seconds,
        warm_ceiling=ceiling_seconds,
        edit_ceiling=ceiling_seconds,
    )
