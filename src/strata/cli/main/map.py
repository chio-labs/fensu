"""Run the strata map command."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TextIO

from strata.cache.mapping.main.build import build_cached_call_map
from strata.cache.mapping.models import CachedCallMap, MapCacheStats
from strata.cli._helpers.map_cache_status import write_map_cache_status
from strata.cli.constants import NO_COLOR_ENVIRONMENT_VARIABLE
from strata.cli.types import ColorMode
from strata.mapping.exceptions import MapError
from strata.mapping.main.ast import build_ast_call_map
from strata.mapping.main.build import build_call_map
from strata.mapping.main.render import render_call_tree
from strata.mapping.main.resolve_project import resolve_mapping_project
from strata.mapping.models import MappingProject
from strata.mapping.types import PathMode


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
        use_color: bool = NO_COLOR_ENVIRONMENT_VARIABLE not in os.environ and (
            args.color == ColorMode.ALWAYS or (args.color == ColorMode.AUTO and stdout.isatty())
        )
        cache_enabled: bool = (
            project.cache_enabled if args.cache_enabled is None else args.cache_enabled
        )
        stats: MapCacheStats | None = None
        if cache_enabled:
            cached: CachedCallMap = build_cached_call_map(
                sources=project.sources,
                symbol=args.symbol,
                depth=args.depth,
                repo_root=project.repo_root,
            )
            stats = cached.stats
            output: str = render_call_tree(
                root=cached.root,
                repo_root=project.repo_root,
                path_mode=PathMode(args.paths),
                use_color=use_color,
            )
        else:
            output = build_call_map(
                sources=project.sources,
                symbol=args.symbol,
                depth=args.depth,
                repo_root=project.repo_root,
                provider=build_ast_call_map,
                path_mode=PathMode(args.paths),
                use_color=use_color,
            )
    except MapError as error:
        stderr.write(f"{error}\n")
        return 2
    write_map_cache_status(stderr=stderr, stats=stats, show_stats=args.cache_stats)
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
    cache_options: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    cache_options.add_argument(
        "--cache", dest="cache_enabled", action="store_true", help="enable map index caching"
    )
    cache_options.add_argument(
        "--no-cache", dest="cache_enabled", action="store_false", help="disable map index caching"
    )
    parser.set_defaults(cache_enabled=None)
    parser.add_argument(
        "--cache-stats", action="store_true", help="write map cache operation counts to stderr"
    )
    return parser


def _nonnegative_int(value: str) -> int:
    parsed: int = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("depth must be zero or greater")
    return parsed
