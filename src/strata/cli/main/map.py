"""Run the strata map command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import RepoRoot
from strata.mapping.core.exceptions import MapError
from strata.mapping.core.main.ast import build_ast_call_map
from strata.mapping.core.main.build import build_call_map


def run_map(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Render a deterministic downstream project call tree."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    config: Config = load_config(Path.cwd())
    repo_root: RepoRoot = discover_files(config).repo_root
    try:
        output: str = build_call_map(
            config=config,
            symbol=args.symbol,
            depth=args.depth,
            repo_root=repo_root.path,
            provider=build_ast_call_map,
        )
    except MapError as error:
        stderr.write(f"{error}\n")
        return 2
    stdout.write(output)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata map")
    parser.add_argument("symbol", help="bare, dotted, or path::function project symbol")
    parser.add_argument("--direction", choices=("downstream",), default="downstream")
    parser.add_argument("--depth", type=_nonnegative_int, default=3, help="maximum call depth")
    return parser


def _nonnegative_int(value: str) -> int:
    parsed: int = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("depth must be zero or greater")
    return parsed
