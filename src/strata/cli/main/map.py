"""Run the strata map command."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TextIO

from strata.cli.core.constants import NO_COLOR_ENVIRONMENT_VARIABLE
from strata.cli.core.types import ColorMode
from strata.mapping.core.exceptions import MapError
from strata.mapping.core.main.ast import build_ast_call_map
from strata.mapping.core.main.build import build_call_map
from strata.mapping.core.main.resolve_project import resolve_mapping_project
from strata.mapping.core.models import MappingProject
from strata.mapping.core.types import PathMode


def run_map(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Render a deterministic downstream project call tree."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    try:
        project: MappingProject = resolve_mapping_project(
            cwd=Path.cwd(), explicit_roots=tuple(args.roots)
        )
        output: str = build_call_map(
            sources=project.sources,
            symbol=args.symbol,
            depth=args.depth,
            repo_root=project.repo_root,
            provider=build_ast_call_map,
            path_mode=PathMode(args.paths),
            use_color=NO_COLOR_ENVIRONMENT_VARIABLE not in os.environ
            and (
                args.color == ColorMode.ALWAYS or (args.color == ColorMode.AUTO and stdout.isatty())
            ),
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
    parser.add_argument(
        "--root",
        dest="roots",
        action="append",
        default=[],
        help="Python import root to map; repeat for multiple roots",
    )
    parser.add_argument(
        "--paths",
        choices=tuple(PathMode),
        default=PathMode.RELATIVE,
        help="path display style",
    )
    parser.add_argument(
        "--color",
        choices=tuple(ColorMode),
        default=ColorMode.AUTO,
        help="ANSI color behavior",
    )
    return parser


def _nonnegative_int(value: str) -> int:
    parsed: int = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("depth must be zero or greater")
    return parsed
