"""Real native integration tests for Strata Memory operations."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from strata.cli.main.memory import run_memory
from strata.memory.exceptions import MemoryOperationError
from strata.memory.main.query_memory import query_memory
from strata.memory.main.read_memory_schema import read_memory_schema
from strata.memory.main.sync_memory import sync_memory
from strata.memory.models import MemoryQueryExecution, MemorySchemaResult, MemorySyncResult
from tests.integration.src.strata.memory.main._test_types import (
    NativeMemoryColorTestCase,
    NativeMemoryErrorTestCase,
    NativeMemoryQueryTestCase,
    NativeMemorySchemaTestCase,
)
from tests.integration.src.strata.memory.main.helpers import write_enabled_memory_project


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryQueryTestCase(
            description="enabled empty repository synchronizes and serves read-only SQL",
            sql="SELECT 7 AS answer, NULL::VARCHAR AS missing",
            expected_columns=("answer", "missing"),
            expected_rows=((7, None),),
            expected_database_relative_path=".strata/memory/memory.duckdb",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_enabled_project_when_syncing_and_querying_then_uses_native_memory_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemoryQueryTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)

    sync_result: MemorySyncResult = sync_memory()
    execution: MemoryQueryExecution = query_memory(sql=test_case.sql, limit=20)

    assert sync_result.project.database_path.is_file()
    assert sync_result.project.database_path.relative_to(tmp_path).as_posix() == (
        test_case.expected_database_relative_path
    )
    assert execution.query.columns == test_case.expected_columns
    assert execution.query.rows == test_case.expected_rows


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryErrorTestCase(
            description="native query rejection maps to stable memory operation error",
            sql="DELETE FROM memory.documents",
            expected_error_fragment="Memory query failed:",
            expected_stdout="",
            expected_exit_code=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mutating_sql_when_querying_then_maps_native_runtime_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemoryErrorTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(MemoryOperationError) as raised:
        _ = query_memory(sql=test_case.sql, limit=20)

    assert test_case.expected_error_fragment in str(raised.value)
    stdout: io.StringIO = io.StringIO()
    stderr: io.StringIO = io.StringIO()
    exit_code: int = run_memory(
        argv=("sql", test_case.sql),
        stdout=stdout,
        stderr=stderr,
    )
    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue() == test_case.expected_stdout
    assert test_case.expected_error_fragment in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemorySchemaTestCase(
            description="focused schema qualifies public name without synchronizing",
            relation="tasks",
            expected_relation="memory.tasks",
            expected_database_exists=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_enabled_project_when_reading_schema_then_does_not_synchronize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemorySchemaTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)

    result: MemorySchemaResult = read_memory_schema(test_case.relation)

    assert result.relation is not None
    assert result.relation.name == test_case.expected_relation
    assert (tmp_path / ".strata/memory/memory.duckdb").exists() is (
        test_case.expected_database_exists
    )


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryColorTestCase(
            description="always color adds ANSI to focused human schema",
            argv=("schema", "tasks", "--color", "always"),
            expected_stdout_fragment="\x1b[1;36mmemory.tasks\x1b[0m",
            expected_absent_fragment="not-present",
            expected_exit_code=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_always_color_when_running_human_memory_command_then_emits_ansi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemoryColorTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NO_COLOR", raising=False)
    stdout: io.StringIO = io.StringIO()
    stderr: io.StringIO = io.StringIO()

    exit_code: int = run_memory(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert test_case.expected_absent_fragment not in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryColorTestCase(
            description="NO_COLOR overrides always color for focused human schema",
            argv=("schema", "tasks", "--color", "always"),
            expected_stdout_fragment="memory.tasks (view)",
            expected_absent_fragment="\x1b[",
            expected_exit_code=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_color_environment_when_running_human_memory_command_then_omits_ansi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemoryColorTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NO_COLOR", "1")
    stdout: io.StringIO = io.StringIO()
    stderr: io.StringIO = io.StringIO()

    exit_code: int = run_memory(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert test_case.expected_absent_fragment not in stdout.getvalue()
