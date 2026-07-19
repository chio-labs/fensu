"""Generate a deterministic performance corpus for Fensu benchmarking."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.perfcorpus.main.run_generation import run_generation


def _parse_args() -> argparse.Namespace:
    """Parse corpus generation command-line arguments."""

    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="perfcorpus_generate")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--files", type=int, default=2400)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    """Generate one seeded corpus and report its summary."""

    args: argparse.Namespace = _parse_args()
    return run_generation(target=args.target, files=args.files, seed=args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
