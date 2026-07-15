"""Run reproducible Strata benchmarks against a configured Python repository."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.benchmarking.main.run import run_benchmark
from scripts.benchmarking.types import OperationProfileMode


def _parse_args() -> argparse.Namespace:
    """Parse benchmark command-line arguments."""

    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="benchmark_check")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    modes: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    modes.add_argument("--profile", action="store_true")
    modes.add_argument(
        "--operations",
        type=OperationProfileMode,
        choices=list(OperationProfileMode),
    )
    parser.add_argument("--executable", type=Path)
    return parser.parse_args()


def main() -> int:
    """Parse benchmark options and delegate to the benchmarking workflow."""

    args: argparse.Namespace = _parse_args()
    return run_benchmark(
        project=args.project,
        runs=args.runs,
        profile=args.profile,
        operations=args.operations,
        executable=args.executable,
    )


if __name__ == "__main__":
    raise SystemExit(main())
