"""Run the Strata Memory command."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from typing import TextIO

from strata.cli.classes.memory_graph_writer import MemoryGraphWriter
from strata.cli.constants import NO_COLOR_ENVIRONMENT_VARIABLE
from strata.cli.types import ColorMode, MemoryCliCommand
from strata.config.exceptions import ConfigError
from strata.memory.constants import (
    DEFAULT_GRAPH_DEPTH,
    DEFAULT_GRAPH_MAX_EDGES,
    DEFAULT_GRAPH_MAX_NODES,
    DEFAULT_QUERY_LIMIT,
    MAX_GRAPH_DEPTH,
    MAX_GRAPH_EDGES,
    MAX_GRAPH_NODES,
    MAX_QUERY_LIMIT,
    MIN_GRAPH_DEPTH,
    MIN_GRAPH_EDGES,
    MIN_GRAPH_NODES,
)
from strata.memory.exceptions import MemoryError
from strata.memory.main.read_memory_schema import read_memory_schema
from strata.memory.main.rebuild_memory import rebuild_memory
from strata.memory.main.render_memory_rebuild import render_memory_rebuild
from strata.memory.main.render_memory_schema import render_memory_schema
from strata.memory.main.render_memory_summary import render_memory_summary
from strata.memory.main.render_memory_sync import render_memory_sync
from strata.memory.main.run_memory_archive import run_memory_archive
from strata.memory.main.run_memory_check import run_memory_check
from strata.memory.main.run_memory_query import run_memory_query
from strata.memory.main.summarize_memory import summarize_memory
from strata.memory.main.sync_memory import sync_memory
from strata.memory.models import MemoryOverviewResult
from strata.memory.types import (
    MemoryGraphDirection,
    MemoryGraphFormat,
    MemoryGraphRelationship,
    MemoryQueryFormat,
)
from strata.reporting.models import RenderedReport


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
        return 0 if error.code == 0 else 2
    try:
        use_color: bool = NO_COLOR_ENVIRONMENT_VARIABLE not in os.environ and (
            args.color == ColorMode.ALWAYS or (args.color == ColorMode.AUTO and stdout.isatty())
        )
        if args.command is None:
            result: MemoryOverviewResult = summarize_memory()
            stdout.write(render_memory_summary(result=result, use_color=use_color))
            return 0
        if args.command == MemoryCliCommand.SYNC:
            stdout.write(render_memory_sync(result=sync_memory(), use_color=use_color))
            return 0
        if args.command == MemoryCliCommand.CHECK:
            report: RenderedReport = run_memory_check(use_color=use_color)
            stdout.write(f"{report.text}\n")
            return 1 if report.fault_count else 0
        if args.command == MemoryCliCommand.ARCHIVE:
            stdout.write(
                run_memory_archive(
                    paths=tuple(args.paths),
                    confirmed=args.yes,
                    use_color=use_color,
                )
            )
            return 0
        if args.command == MemoryCliCommand.REBUILD:
            stdout.write(render_memory_rebuild(result=rebuild_memory(), use_color=use_color))
            return 0
        if args.command == MemoryCliCommand.SCHEMA:
            stdout.write(
                render_memory_schema(result=read_memory_schema(args.relation), use_color=use_color)
            )
            return 0
        if args.command == MemoryCliCommand.GRAPH:
            MemoryGraphWriter.write(
                args=args,
                stdout=stdout,
                stderr=stderr,
                use_color=use_color,
            )
            return 0
        limit: int = MAX_QUERY_LIMIT if args.no_limit else args.limit
        sync_text, query_text = run_memory_query(
            sql=args.query,
            limit=limit,
            output_format=args.output_format,
            use_color=use_color,
        )
        stderr.write(sync_text)
        stdout.write(query_text)
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
        dest="command", metavar="{archive,check,sync,rebuild,schema,graph,sql}"
    )
    archive_parser: argparse.ArgumentParser = subparsers.add_parser(
        MemoryCliCommand.ARCHIVE, help="archive eligible or explicit memory sources"
    )
    archive_parser.add_argument("paths", nargs="*", help="repository-relative canonical paths")
    archive_parser.add_argument("--yes", action="store_true", help="confirm explicit task archive")
    archive_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
    check_parser: argparse.ArgumentParser = subparsers.add_parser(
        MemoryCliCommand.CHECK, help="validate canonical memory sources"
    )
    check_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
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
    graph_parser: argparse.ArgumentParser = subparsers.add_parser(
        MemoryCliCommand.GRAPH, help="retrieve a bounded document relationship graph"
    )
    graph_parser.add_argument("pattern", metavar="DOCUMENT_OR_PATTERN")
    graph_parser.add_argument(
        "--direction", choices=tuple(MemoryGraphDirection), default=MemoryGraphDirection.OUTBOUND
    )
    graph_parser.add_argument(
        "--relationship",
        dest="relationships",
        choices=tuple(MemoryGraphRelationship),
        action="append",
        default=[],
    )
    graph_parser.add_argument(
        "--depth",
        type=lambda value: _bounded_integer(
            value=value, name="depth", minimum=MIN_GRAPH_DEPTH, maximum=MAX_GRAPH_DEPTH
        ),
        default=DEFAULT_GRAPH_DEPTH,
    )
    graph_parser.add_argument(
        "--max-nodes",
        type=lambda value: _bounded_integer(
            value=value,
            name="max-nodes",
            minimum=MIN_GRAPH_NODES,
            maximum=MAX_GRAPH_NODES,
        ),
        default=DEFAULT_GRAPH_MAX_NODES,
    )
    graph_parser.add_argument(
        "--max-edges",
        type=lambda value: _bounded_integer(
            value=value,
            name="max-edges",
            minimum=MIN_GRAPH_EDGES,
            maximum=MAX_GRAPH_EDGES,
        ),
        default=DEFAULT_GRAPH_MAX_EDGES,
    )
    graph_parser.add_argument("--include-archived", action="store_true")
    graph_parser.add_argument(
        "--format",
        dest="output_format",
        choices=tuple(MemoryGraphFormat),
        default=MemoryGraphFormat.LONG,
    )
    graph_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
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
    limits.add_argument(
        "--limit",
        type=lambda value: _bounded_integer(
            value=value, name="limit", minimum=1, maximum=MAX_QUERY_LIMIT
        ),
        default=DEFAULT_QUERY_LIMIT,
    )
    limits.add_argument("--no-limit", action="store_true")
    sql_parser.add_argument("--color", choices=tuple(ColorMode), default=argparse.SUPPRESS)
    return parser


def _bounded_integer(*, value: str, name: str, minimum: int, maximum: int) -> int:
    parsed: int = int(value)
    if not minimum <= parsed <= maximum:
        raise argparse.ArgumentTypeError(f"{name} must be between {minimum} and {maximum}")
    return parsed
