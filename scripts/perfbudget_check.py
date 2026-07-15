"""Enforce wall-clock performance budgets over the generated corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.perfbudget.constants import DEFAULT_FILE_TARGET, DEFAULT_SEED
from scripts.perfbudget.main.run_budget import run_budget
from strata.analysis.types import FactBackend


def _parse_args() -> argparse.Namespace:
    """Parse budget command-line arguments."""

    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="perfbudget_check")
    parser.add_argument("--executable", type=Path, default=None)
    parser.add_argument(
        "--backend",
        choices=[FactBackend.PYTHON.value, FactBackend.NATIVE.value],
        default=FactBackend.PYTHON.value,
    )
    parser.add_argument("--files", type=int, default=DEFAULT_FILE_TARGET)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--uncached-ceiling", type=float, default=None)
    parser.add_argument("--cold-ceiling", type=float, default=None)
    parser.add_argument("--warm-ceiling", type=float, default=None)
    parser.add_argument("--edit-ceiling", type=float, default=None)
    return parser.parse_args()


def main() -> int:
    """Run every budget scenario and enforce the configured ceilings."""

    args: argparse.Namespace = _parse_args()
    return run_budget(
        backend=args.backend,
        files=args.files,
        seed=args.seed,
        runs=args.runs,
        uncached_ceiling=args.uncached_ceiling,
        cold_ceiling=args.cold_ceiling,
        warm_ceiling=args.warm_ceiling,
        edit_ceiling=args.edit_ceiling,
        executable=args.executable,
    )


if __name__ == "__main__":
    raise SystemExit(main())
