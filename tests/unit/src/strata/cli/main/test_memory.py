"""Tests for the Strata Memory command adapter."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from strata.cli.main.memory import run_memory
from tests.unit.src.strata.cli.main._test_types import (
    MemoryAdapterTestCase,
    MemoryDisabledAdapterTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryAdapterTestCase(
            description="memory help documents every initial subcommand and color option",
            argv=("--help",),
            expected_stdout=(
                "usage: strata memory [-h] [--color {auto,always,never}]\n"
                "                     {archive,check,sync,rebuild,schema,graph,sql} ...\n\n"
                "Synchronize, inspect, and query persistent repository memory.\n\n"
                "positional arguments:\n"
                "  {archive,check,sync,rebuild,schema,graph,sql}\n"
                "    archive             archive eligible or explicit memory sources\n"
                "    check               validate canonical memory sources\n"
                "    sync                synchronize changed sources\n"
                "    rebuild             replace the complete memory index\n"
                "    schema              show public relation metadata\n"
                "    graph               retrieve a bounded document relationship graph\n"
                "    sql                 run read-only SQL\n\n"
                "options:\n"
                "  -h, --help            show this help message and exit\n"
                "  --color {auto,always,never}\n"
                "                        ANSI color behavior\n"
            ),
            expected_stderr_fragment="",
            expected_exit_code=0,
        ),
        MemoryAdapterTestCase(
            description="graph help documents the frozen traversal surface",
            argv=("graph", "--help"),
            expected_stdout=(
                "usage: strata memory graph [-h] [--direction {outbound,inbound,both}]\n"
                "                           [--relationship {link,related,depends-on,supersedes,discovered-from,implements,documents}]\n"
                "                           [--depth DEPTH] [--max-nodes MAX_NODES]\n"
                "                           [--max-edges MAX_EDGES] [--include-archived]\n"
                "                           [--format {long,json}]\n"
                "                           [--color {auto,always,never}]\n"
                "                           DOCUMENT_OR_PATTERN\n\n"
                "positional arguments:\n"
                "  DOCUMENT_OR_PATTERN\n\n"
                "options:\n"
                "  -h, --help            show this help message and exit\n"
                "  --direction {outbound,inbound,both}\n"
                "  --relationship {link,related,depends-on,supersedes,discovered-from,implements,documents}\n"
                "  --depth DEPTH\n"
                "  --max-nodes MAX_NODES\n"
                "  --max-edges MAX_EDGES\n"
                "  --include-archived\n"
                "  --format {long,json}\n"
                "  --color {auto,always,never}\n"
            ),
            expected_stderr_fragment="",
            expected_exit_code=0,
        ),
        MemoryAdapterTestCase(
            description="graph depth below the frozen bound is rejected",
            argv=("graph", "alpha", "--depth", "0"),
            expected_stdout="",
            expected_stderr_fragment="depth must be between 1 and 5",
            expected_exit_code=2,
        ),
        MemoryAdapterTestCase(
            description="graph node budget above the frozen bound is rejected",
            argv=("graph", "alpha", "--max-nodes", "201"),
            expected_stdout="",
            expected_stderr_fragment="max-nodes must be between 1 and 200",
            expected_exit_code=2,
        ),
        MemoryAdapterTestCase(
            description="graph edge budget above the frozen bound is rejected",
            argv=("graph", "alpha", "--max-edges", "501"),
            expected_stdout="",
            expected_stderr_fragment="max-edges must be between 1 and 500",
            expected_exit_code=2,
        ),
        MemoryAdapterTestCase(
            description="unknown graph relationship is rejected",
            argv=("graph", "alpha", "--relationship", "unknown"),
            expected_stdout="",
            expected_stderr_fragment="invalid choice: 'unknown'",
            expected_exit_code=2,
        ),
        MemoryAdapterTestCase(
            description="unknown memory command returns argparse usage error",
            argv=("unknown",),
            expected_stdout="",
            expected_stderr_fragment="invalid choice: 'unknown'",
            expected_exit_code=2,
        ),
        MemoryAdapterTestCase(
            description="query limit below the native minimum is rejected",
            argv=("sql", "SELECT 1", "--limit", "0"),
            expected_stdout="",
            expected_stderr_fragment="limit must be between 1 and 1000",
            expected_exit_code=2,
        ),
        MemoryAdapterTestCase(
            description="query limit and no-limit options are mutually exclusive",
            argv=("sql", "SELECT 1", "--limit", "2", "--no-limit"),
            expected_stdout="",
            expected_stderr_fragment="not allowed with argument --limit",
            expected_exit_code=2,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_memory_arguments_when_running_adapter_then_returns_expected_parser_contract(
    test_case: MemoryAdapterTestCase,
) -> None:
    stdout: io.StringIO = io.StringIO()
    stderr: io.StringIO = io.StringIO()

    exit_code: int = run_memory(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue() == test_case.expected_stdout
    assert test_case.expected_stderr_fragment in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryDisabledAdapterTestCase(
            description="bare memory requires explicit enablement",
            argv=(),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
        MemoryDisabledAdapterTestCase(
            description="memory archive requires explicit enablement",
            argv=("archive",),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
        MemoryDisabledAdapterTestCase(
            description="memory check requires explicit enablement",
            argv=("check",),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
        MemoryDisabledAdapterTestCase(
            description="memory sync requires explicit enablement",
            argv=("sync",),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
        MemoryDisabledAdapterTestCase(
            description="memory rebuild requires explicit enablement",
            argv=("rebuild",),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
        MemoryDisabledAdapterTestCase(
            description="memory schema requires explicit enablement",
            argv=("schema",),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
        MemoryDisabledAdapterTestCase(
            description="memory graph requires explicit enablement",
            argv=("graph", "alpha"),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
        MemoryDisabledAdapterTestCase(
            description="memory SQL requires explicit enablement",
            argv=("sql", "SELECT 1"),
            expected_error_fragment="Strata Memory is disabled",
            expected_database_exists=False,
            expected_exit_code=2,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_disabled_memory_when_running_command_then_fails_before_database_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: MemoryDisabledAdapterTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src"]\n[memory]\nenabled = false\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    stdout: io.StringIO = io.StringIO()
    stderr: io.StringIO = io.StringIO()

    exit_code: int = run_memory(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert (tmp_path / ".strata/memory/memory.duckdb").exists() is (
        test_case.expected_database_exists
    )
