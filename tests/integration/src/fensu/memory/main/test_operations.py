"""Real native integration tests for Fensu Memory operations."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import cast

import pytest

from fensu.cli.main.memory import run_memory
from fensu.memory.constants import MEMORY_DIRECTORIES, MEMORY_GITIGNORE_ENTRY
from fensu.memory.exceptions import MemoryOperationError
from fensu.memory.main._query_memory import query_memory
from fensu.memory.main.read_memory_schema import read_memory_schema
from fensu.memory.main.sync_memory import sync_memory
from fensu.memory.models import MemoryQueryExecution, MemorySchemaResult, MemorySyncResult
from tests.integration.src.fensu.memory.main._test_types import (
    MemoryBootstrapTestCase,
    NativeMemoryArchiveTestCase,
    NativeMemoryCheckTestCase,
    NativeMemoryColorTestCase,
    NativeMemoryErrorTestCase,
    NativeMemoryGraphTestCase,
    NativeMemoryQueryTestCase,
    NativeMemorySchemaTestCase,
)
from tests.integration.src.fensu.memory.main.helpers import write_enabled_memory_project


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryBootstrapTestCase(
            description="first enabled operation creates canonical state exactly once",
            existing_relative_path=None,
            expected_error_fragment="",
            expected_gitignore_exists=True,
            expected_canonical_directories=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_enabled_project_without_memory_tree_when_resolving_twice_then_bootstraps_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: MemoryBootstrapTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)

    _ = read_memory_schema("tasks")
    first_gitignore: bytes = (tmp_path / ".gitignore").read_bytes()
    _ = read_memory_schema("tasks")

    assert (tmp_path / ".gitignore").exists() is test_case.expected_gitignore_exists
    assert first_gitignore == (tmp_path / ".gitignore").read_bytes()
    assert first_gitignore.count(MEMORY_GITIGNORE_ENTRY.encode()) == 1
    assert (
        all((tmp_path / path).is_dir() for path in MEMORY_DIRECTORIES)
        is test_case.expected_canonical_directories
    )


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryBootstrapTestCase(
            description="noncanonical existing tree is refused before bootstrap writes",
            existing_relative_path=".ai/legacy.md",
            expected_error_fragment="will not be migrated automatically",
            expected_gitignore_exists=False,
            expected_canonical_directories=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_noncanonical_existing_tree_when_resolving_memory_then_refuses_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: MemoryBootstrapTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    existing: Path = tmp_path / str(test_case.existing_relative_path)
    existing.parent.mkdir(parents=True)
    existing.write_text("# Legacy\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(MemoryOperationError) as raised:
        _ = read_memory_schema("tasks")

    assert test_case.expected_error_fragment in str(raised.value)
    assert (tmp_path / ".gitignore").exists() is test_case.expected_gitignore_exists
    assert (
        all((tmp_path / path).is_dir() for path in MEMORY_DIRECTORIES)
        is test_case.expected_canonical_directories
    )
    assert existing.read_text(encoding="utf-8") == "# Legacy\n"


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryQueryTestCase(
            description="enabled empty repository synchronizes and serves read-only SQL",
            sql="SELECT 7 AS answer, CAST(NULL AS TEXT) AS missing",
            expected_columns=("answer", "missing"),
            expected_rows=((7, None),),
            expected_database_relative_path=".fensu/memory/memory.sqlite3",
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
    assert (tmp_path / ".fensu/memory/memory.sqlite3").exists() is (
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


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryCheckTestCase(
            description="invalid root Markdown reports MEM002 and prevents publication",
            relative_path=".ai/orphan.md",
            contents="# Orphan\n",
            expected_fault_fragment="MEM002",
            expected_database_exists=False,
            expected_exit_code=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_memory_source_when_checking_then_reports_fault_without_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemoryCheckTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    _ = read_memory_schema("tasks")
    source: Path = tmp_path / test_case.relative_path
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(test_case.contents, encoding="utf-8")
    stdout: io.StringIO = io.StringIO()

    exit_code: int = run_memory(argv=("check",), stdout=stdout, stderr=io.StringIO())

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_fault_fragment in stdout.getvalue()
    assert (tmp_path / ".fensu/memory/memory.sqlite3").exists() is (
        test_case.expected_database_exists
    )


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryArchiveTestCase(
            description="explicit note archive moves source and refreshes generated index",
            relative_path=(".ai/knowledge/repo/notes/20260717T120000_000000Z__NOTE-archive.md"),
            contents="# Archive\n",
            expected_destination=(
                ".ai/_archive/knowledge/repo/notes/20260717T120000_000000Z__NOTE-archive.md"
            ),
            expected_output_fragment="Memory archived",
            expected_exit_code=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_note_when_archiving_then_moves_source_and_refreshes_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemoryArchiveTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    source: Path = tmp_path / test_case.relative_path
    source.parent.mkdir(parents=True)
    source.write_text(test_case.contents, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stdout: io.StringIO = io.StringIO()

    exit_code: int = run_memory(
        argv=("archive", test_case.relative_path),
        stdout=stdout,
        stderr=io.StringIO(),
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert not source.exists()
    assert (tmp_path / test_case.expected_destination).is_file()
    assert (tmp_path / ".fensu/memory/memory.sqlite3").is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        NativeMemoryGraphTestCase(
            description="graph CLI synchronizes separately and returns deterministic bounded JSON",
            files=(
                (
                    ".ai/knowledge/repo/notes/20260718T120001_000000Z__NOTE-alpha.md",
                    "# Alpha\n\n[[beta]]\n\n[[archived]]\n\n"
                    "[external](https://example.com)\n\n[[missing]]\n",
                ),
                (
                    ".ai/knowledge/repo/notes/20260718T120002_000000Z__NOTE-beta.md",
                    "# Beta\n\n[[alpha]]\n",
                ),
                (
                    ".ai/_archive/knowledge/repo/notes/20260718T120003_000000Z__NOTE-archived.md",
                    "# Archived\n\n[[delta]]\n",
                ),
                (
                    ".ai/knowledge/repo/notes/20260718T120004_000000Z__NOTE-delta.md",
                    "# Delta\n",
                ),
            ),
            argv=("graph", "Alpha", "--depth", "2", "--format", "json"),
            expected_selection="exact",
            expected_root="note:20260718T120001_000000Z",
            expected_node_count=3,
            expected_edge_statuses=("external", "resolved", "unresolved"),
            expected_archived_identity="note:20260718T120003_000000Z",
            expected_absent_identity="note:20260718T120004_000000Z",
            expected_sync_fragment="Memory synced:",
            expected_sources_unchanged=True,
            expected_exit_code=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_enabled_graph_sources_when_running_cli_then_separates_sync_and_machine_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: NativeMemoryGraphTestCase,
) -> None:
    write_enabled_memory_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    _ = read_memory_schema("tasks")
    for relative_path, contents in test_case.files:
        source: Path = tmp_path / relative_path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(contents, encoding="utf-8")
    first_stdout: io.StringIO = io.StringIO()
    first_stderr: io.StringIO = io.StringIO()

    first_exit_code: int = run_memory(argv=test_case.argv, stdout=first_stdout, stderr=first_stderr)
    second_stdout: io.StringIO = io.StringIO()
    second_stderr: io.StringIO = io.StringIO()
    second_exit_code: int = run_memory(
        argv=test_case.argv, stdout=second_stdout, stderr=second_stderr
    )
    payload: dict[str, object] = json.loads(first_stdout.getvalue())
    nodes: list[dict[str, object]] = cast(list[dict[str, object]], payload["nodes"])
    edges: list[dict[str, object]] = cast(list[dict[str, object]], payload["edges"])

    assert first_exit_code == test_case.expected_exit_code
    assert second_exit_code == test_case.expected_exit_code
    assert test_case.expected_sync_fragment in first_stderr.getvalue()
    assert second_stderr.getvalue() == ""
    assert first_stdout.getvalue() == second_stdout.getvalue()
    assert payload["selection"] == test_case.expected_selection
    assert payload["roots"] == [test_case.expected_root]
    assert len(nodes) == test_case.expected_node_count
    assert test_case.expected_archived_identity in {node["identity"] for node in nodes}
    assert test_case.expected_absent_identity not in {node["identity"] for node in nodes}
    assert test_case.expected_edge_statuses == tuple(
        sorted({str(edge["resolution_status"]) for edge in edges})
    )
    assert any(edge["cycle"] is True for edge in edges)
    assert (
        all(
            (tmp_path / relative_path).read_text(encoding="utf-8") == contents
            for relative_path, contents in test_case.files
        )
        is test_case.expected_sources_unchanged
    )
