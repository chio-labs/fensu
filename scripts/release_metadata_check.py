"""Reject release branches containing non-generated metadata changes."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.release_metadata.main.run_release_metadata_check import run_release_metadata_check


def _parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="release_metadata_check")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    """Validate one generated release delta and render actionable failures."""

    arguments: argparse.Namespace = _parse_args()
    return run_release_metadata_check(
        repo_root=arguments.repo,
        base_ref=arguments.base,
        head_ref=arguments.head,
    )


if __name__ == "__main__":
    raise SystemExit(main())
