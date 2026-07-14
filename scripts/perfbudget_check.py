"""Enforce wall-clock performance budgets over the generated corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.perfbudget.constants import (
    DEFAULT_COLD_CEILING_SECONDS,
    DEFAULT_EDIT_CEILING_SECONDS,
    DEFAULT_FILE_TARGET,
    DEFAULT_SEED,
    DEFAULT_UNCACHED_CEILING_SECONDS,
    DEFAULT_WARM_CEILING_SECONDS,
)
from scripts.perfbudget.main.run_budget import run_budget


def _parse_args() -> argparse.Namespace:
    """Parse budget command-line arguments."""

    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="perfbudget_check")
    parser.add_argument("--executable", type=Path, default=None)
    parser.add_argument("--files", type=int, default=DEFAULT_FILE_TARGET)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--uncached-ceiling", type=float, default=DEFAULT_UNCACHED_CEILING_SECONDS)
    parser.add_argument("--cold-ceiling", type=float, default=DEFAULT_COLD_CEILING_SECONDS)
    parser.add_argument("--warm-ceiling", type=float, default=DEFAULT_WARM_CEILING_SECONDS)
    parser.add_argument("--edit-ceiling", type=float, default=DEFAULT_EDIT_CEILING_SECONDS)
    return parser.parse_args()


def main() -> int:
    """Run every budget scenario and enforce the configured ceilings."""

    args: argparse.Namespace = _parse_args()
    return run_budget(
        files=args.files,
        seed=args.seed,
        uncached_ceiling=args.uncached_ceiling,
        cold_ceiling=args.cold_ceiling,
        warm_ceiling=args.warm_ceiling,
        edit_ceiling=args.edit_ceiling,
        executable=args.executable,
    )


if __name__ == "__main__":
    raise SystemExit(main())
