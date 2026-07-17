"""Run the Strata Memory command."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from typing import TextIO

from strata.cli.constants import NO_COLOR_ENVIRONMENT_VARIABLE
from strata.cli.types import ColorMode, MemoryCliCommand
from strata.config.exceptions import ConfigError
from strata.memory.constants import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT
from strata.memory.exceptions import MemoryError
from strata.memory.main.query_memory import query_memory
from strata.memory.main.read_memory_schema import read_memory_schema
from strata.memory.main.rebuild_memory import rebuild_memory
from strata.memory.main.render_memory_overview import render_memory_overview
from strata.memory.main.render_memory_query import render_memory_query
from strata.memory.main.render_memory_rebuild import render_memory_rebuild
from strata.memory.main.render_memory_schema import render_memory_schema
from strata.memory.main.render_memory_sync import render_memory_sync
from strata.memory.main.summarize_memory import summarize_memory
from strata.memory.main.sync_memory import sync_memory
from strata.memory.models import MemoryOverviewResult, MemoryQueryExecution, MemorySyncResult
from strata.memory.types import MemoryQueryFormat


def run_memory(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Parse and execute one Strata Memory command."""

    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    except SystemExit as error:
        exit_code: object = error.code
        return exit_code if isinstance(exit_code, int) else 2
    try:
        use_color: bool = NO_COLOR_ENVIRONMENT_VARIABLE not in os.environ and (
            args.color == ColorMode.ALWAYS or (args.color == ColorMode.AUTO and stdout.isatty())
        )
        if args.command is None:
            result: MemoryOverviewResult = summarize_memory()
            sync_result: MemorySyncResult = MemorySyncResult(
                project=result.project, sync=result.sync
            )
            stdout.write(render_memory_sync(result=sync_result, compact=True, use_color=use_color))
            stdout.write(render_memory_overview(result=result, use_color=use_color))
            return 0
        if args.command == MemoryCliCommand.SYNC:
            stdout.write(render_memory_sync(result=sync_memory(), use_color=use_color))
            return 0
        if args.command == MemoryCliCommand.REBUILD:
            stdout.write(render_memory_rebuild(result=rebuild_memory(), use_color=use_color))
            return 0
        if args.command == MemoryCliCommand.SCHEMA:
            stdout.write(
                render_memory_schema(result=read_memory_schema(args.relation), use_color=use_color)
            )
            return 0
        limit: int = MAX_QUERY_LIMIT if args.no_limit else args.limit
        execution: MemoryQueryExecution = query_memory(sql=args.query, limit=limit)
        output_format: MemoryQueryFormat = MemoryQueryFormat(args.output_format)
        query_color: bool = use_color and output_format in {
            MemoryQueryFormat.LONG,
            MemoryQueryFormat.TABLE,
        }
        query_sync: MemorySyncResult = MemorySyncResult(
            project=execution.project, sync=execution.sync
        )
        stderr.write(render_memory_sync(result=query_sync, compact=True, use_color=query_color))
        stdout.write(
            render_memory_query(
                result=execution.query,
                output_format=output_format,
                use_color=query_color,
            )
        )
        return 0
    except (ConfigError, MemoryError) as error:
        stderr.write(f"{error}\n")
        return 2


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="strata memory",
        description="Synchronize, inspect, and query persistent repository memory.",
    )
    parser.add_argument(
        "--color", choices=tuple(ColorMode), default=ColorMode.AUTO, help="ANSI color behavior"
    )
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="command", metavar="{sync,rebuild,schema,sql}"
    )
    sync_parser: argparse.ArgumentParser = subparsers.add_parser(
        MemoryCliCommand.SYNC, help="synchronize changed sources"
    )
    sync_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
    rebuild_parser: argparse.ArgumentParser = subparsers.add_parser(
        MemoryCliCommand.REBUILD, help="replace the complete memory index"
    )
    rebuild_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
    schema_parser: argparse.ArgumentParser = subparsers.add_parser(
        MemoryCliCommand.SCHEMA, help="show public relation metadata"
    )
    schema_parser.add_argument("relation", nargs="?", help="public relation name")
    schema_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
    sql_parser: argparse.ArgumentParser = subparsers.add_parser(
        MemoryCliCommand.SQL, help="run read-only SQL"
    )
    sql_parser.add_argument("query", metavar="QUERY", help="read-only SQL query")
    sql_parser.add_argument(
        "--format",
        dest="output_format",
        choices=tuple(MemoryQueryFormat),
        default=MemoryQueryFormat.LONG,
    )
    limits: argparse._MutuallyExclusiveGroup = sql_parser.add_mutually_exclusive_group()
    limits.add_argument("--limit", type=_query_limit, default=DEFAULT_QUERY_LIMIT)
    limits.add_argument("--no-limit", action="store_true")
    sql_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
    return parser


def _query_limit(value: str) -> int:
    parsed: int = int(value)
    if not 1 <= parsed <= MAX_QUERY_LIMIT:
        raise argparse.ArgumentTypeError(f"limit must be between 1 and {MAX_QUERY_LIMIT}")
    return parsed
