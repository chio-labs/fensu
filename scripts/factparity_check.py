"""Compare Python and native fact backends for exact family parity."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.factparity.constants import DEFAULT_ROOT_NAMES
from scripts.factparity.main.run_parity import run_parity


def _parse_args() -> tuple[Path, ...]:
    """Parse parity command-line arguments into comparison roots."""

    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="factparity_check")
    parser.add_argument("--root", action="append", type=Path, default=None)
    args: argparse.Namespace = parser.parse_args()
    if args.root:
        return tuple(args.root)
    return tuple(Path(name) for name in DEFAULT_ROOT_NAMES)


def main() -> int:
    """Run parity comparison over the requested roots."""

    return run_parity(roots=_parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
