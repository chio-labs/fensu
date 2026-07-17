"""Tests for deterministic Strata Memory renderers."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.memory.main._render_memory_overview import render_memory_overview
from strata.memory.main._render_memory_query import render_memory_query
from strata.memory.main.render_memory_check import render_memory_check
from strata.memory.main.render_memory_rebuild import render_memory_rebuild
from strata.memory.main.render_memory_schema import render_memory_schema
from strata.memory.main.render_memory_sync import render_memory_sync
from strata.memory.models import (
    MemoryCheckResult,
    MemoryDiagnostic,
    MemoryIndexSummary,
    MemoryOverview,
    MemoryOverviewResult,
    MemoryProject,
    MemoryQueryResult,
    MemoryRebuildResult,
    MemoryRelationSchema,
    MemorySchema,
    MemorySchemaColumn,
    MemorySchemaRelation,
    MemorySchemaResult,
    MemorySyncResult,
    MemorySyncSummary,
)
from strata.memory.types import MemoryQueryFormat
from strata.reporting.models import RenderedReport
from tests.unit.src.strata.memory._test_types import (
    MemoryCheckRenderTestCase,
    MemoryOverviewRenderTestCase,
    MemoryQueryRenderTestCase,
    MemoryRebuildRenderTestCase,
    MemorySchemaRenderTestCase,
    MemorySyncRenderTestCase,
)

_PROJECT: MemoryProject = MemoryProject(
    repository_root=Path("/repo"),
    database_path=Path("/repo/.strata/memory/memory.duckdb"),
)
_QUERY_RESULT: MemoryQueryResult = MemoryQueryResult(
    columns=("value", "value"),
    types=("INTEGER", "VARCHAR"),
    rows=((1, None),),
    truncated=True,
)


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryQueryRenderTestCase(
            description="expanded records preserve duplicate columns and report truncation",
            result=_QUERY_RESULT,
            output_format=MemoryQueryFormat.LONG,
            expected_output=("-[ RECORD 1 ]-\nvalue | 1\nvalue | NULL\n(1 row, truncated)\n"),
        ),
        MemoryQueryRenderTestCase(
            description="simple table output is deterministic and reports truncation",
            result=_QUERY_RESULT,
            output_format=MemoryQueryFormat.TABLE,
            expected_output=("value | value\n------+------\n1     | NULL\n(1 row, truncated)\n"),
        ),
        MemoryQueryRenderTestCase(
            description="JSON envelope preserves duplicate columns metadata and nulls",
            result=_QUERY_RESULT,
            output_format=MemoryQueryFormat.JSON,
            expected_output=(
                '{"columns":["value","value"],"types":["INTEGER","VARCHAR"],'
                '"rows":[[1,null]],"truncated":true}\n'
            ),
        ),
        MemoryQueryRenderTestCase(
            description="JSON recursively preserves arrays and objects as safe values",
            result=MemoryQueryResult(
                columns=("nested", "nested"),
                types=("INTEGER[]", "STRUCT"),
                rows=(([1, None], {"active": True}),),
                truncated=False,
            ),
            output_format=MemoryQueryFormat.JSON,
            expected_output=(
                '{"columns":["nested","nested"],"types":["INTEGER[]","STRUCT"],'
                '"rows":[[[1,null],{"active":true}]],"truncated":false}\n'
            ),
        ),
        MemoryQueryRenderTestCase(
            description="CSV uses RFC line endings and explicit NULL text",
            result=_QUERY_RESULT,
            output_format=MemoryQueryFormat.CSV,
            expected_output="value,value\r\n1,NULL\r\n",
        ),
        MemoryQueryRenderTestCase(
            description="CSV quotes embedded delimiters and quote characters",
            result=MemoryQueryResult(
                columns=("text",),
                types=("VARCHAR",),
                rows=(('a,"b"',),),
                truncated=False,
            ),
            output_format=MemoryQueryFormat.CSV,
            expected_output='text\r\n"a,""b"""\r\n',
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_query_result_when_rendering_format_then_matches_output_contract(
    test_case: MemoryQueryRenderTestCase,
) -> None:
    rendered: str = render_memory_query(
        result=test_case.result,
        output_format=test_case.output_format,
    )

    assert rendered == test_case.expected_output


@pytest.mark.parametrize(
    "test_case",
    [
        MemorySchemaRenderTestCase(
            description="schema overview groups stored tables before convenience views",
            result=MemorySchemaResult(
                project=_PROJECT,
                schema=MemorySchema(
                    schema_version=1,
                    parser_contract_version=2,
                    relations=(
                        MemorySchemaRelation("memory.documents", "table", "Stored documents."),
                        MemorySchemaRelation("memory.tasks", "view", "Task history."),
                    ),
                ),
                relation=None,
            ),
            expected_output=(
                "Memory schema 1 (parser contract 2)\n\n"
                "Stored tables:\n  memory.documents  Stored documents.\n\n"
                "Convenience views:\n  memory.tasks  Task history.\n"
            ),
        ),
        MemorySchemaRenderTestCase(
            description="focused schema shows qualified relation columns and meanings",
            result=MemorySchemaResult(
                project=_PROJECT,
                schema=None,
                relation=MemoryRelationSchema(
                    name="memory.tasks",
                    kind="view",
                    comment="Task history.",
                    columns=(MemorySchemaColumn("identity", "VARCHAR", False, "Stable identity."),),
                ),
            ),
            expected_output=(
                "memory.tasks (view)\nTask history.\n\n"
                "Column   | Type    | Nullable | Meaning\n"
                "---------+---------+----------+-----------------\n"
                "identity | VARCHAR | no       | Stable identity.\n"
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_schema_metadata_when_rendering_then_matches_public_relation_contract(
    test_case: MemorySchemaRenderTestCase,
) -> None:
    rendered: str = render_memory_schema(result=test_case.result)

    assert rendered == test_case.expected_output


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryOverviewRenderTestCase(
            description="compact overview reports plan families and SQL hint",
            result=MemoryOverviewResult(
                project=_PROJECT,
                sync=MemorySyncSummary(0, 0, 0, 0, 3, False, False, 3, 4, 1),
                overview=MemoryOverview(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
            ),
            expected_output=(
                "Tasks: 1 not started, 2 in progress, 3 completed, 4 cancelled, 5 superseded\n"
                "Knowledge: 6 notes, 7 decisions, 8 skills\n"
                "Archive: 9 tasks, 10 knowledge\n"
                "Index: 11 documents, 12 sections\n"
                'SQL: strata memory sql "SELECT * FROM memory.current_tasks"\n'
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_memory_overview_when_rendering_then_matches_compact_plan_contract(
    test_case: MemoryOverviewRenderTestCase,
) -> None:
    rendered: str = render_memory_overview(result=test_case.result)

    assert rendered == test_case.expected_output


@pytest.mark.parametrize(
    "test_case",
    [
        MemorySyncRenderTestCase(
            description="unchanged implicit sync is silent",
            result=MemorySyncResult(
                project=_PROJECT,
                sync=MemorySyncSummary(0, 0, 0, 0, 3, False, False, 3, 4, 1),
            ),
            compact=True,
            expected_output="",
        ),
        MemorySyncRenderTestCase(
            description="changed implicit sync uses one concise line",
            result=MemorySyncResult(
                project=_PROJECT,
                sync=MemorySyncSummary(1, 2, 3, 4, 0, False, True, 3, 4, 1),
            ),
            compact=True,
            expected_output="Memory synced: +1 ~2 >3 -4\n",
        ),
        MemorySyncRenderTestCase(
            description="explicit sync reports all counts and the database path",
            result=MemorySyncResult(
                project=_PROJECT,
                sync=MemorySyncSummary(1, 2, 3, 4, 5, True, True, 6, 7, 8),
            ),
            compact=False,
            expected_output=(
                "Memory sync: added=1 changed=2 moved=3 removed=4 unchanged=5 rebuilt=yes\n"
                "Index: documents=6 sections=7 links=8\n"
                "Repository: /repo\n"
                "Database: /repo/.strata/memory/memory.duckdb\n"
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_implicit_sync_when_rendering_then_obeys_concise_output_contract(
    test_case: MemorySyncRenderTestCase,
) -> None:
    rendered: str = render_memory_sync(result=test_case.result, compact=test_case.compact)

    assert rendered == test_case.expected_output


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryRebuildRenderTestCase(
            description="explicit rebuild reports deterministic counts and database path",
            result=MemoryRebuildResult(
                project=_PROJECT,
                summary=MemoryIndexSummary(1, 2, 3, 4, 5, 6, 7, 8, 9),
            ),
            expected_output=(
                "Memory rebuilt: documents=1 sections=2 list_items=3 links=4 "
                "tags=5 skill_files=6\n"
                "Diagnostics: source=7 corpus=8 graph=9\n"
                "Repository: /repo\n"
                "Database: /repo/.strata/memory/memory.duckdb\n"
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rebuild_result_when_rendering_then_reports_counts_and_path(
    test_case: MemoryRebuildRenderTestCase,
) -> None:
    rendered: str = render_memory_rebuild(result=test_case.result)

    assert rendered == test_case.expected_output


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryCheckRenderTestCase(
            description="memory findings reuse standard locations and remediation output",
            result=MemoryCheckResult(
                project=_PROJECT,
                diagnostics=(
                    MemoryDiagnostic(
                        code="MEM002",
                        repository_relative_path=".ai/orphan.md",
                        line=None,
                        column=None,
                        message="root-level Markdown is not canonical",
                        remediation="Move the source into its canonical knowledge location.",
                    ),
                ),
                published=None,
            ),
            expected_output=(
                "MEM002  root-level Markdown is not canonical\n"
                " --> .ai/orphan.md:-:-\n"
                "  = help: Move the source into its canonical knowledge location.\n\n"
                "Found 1 fault"
            ),
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_memory_findings_when_rendering_then_uses_standard_fault_language(
    test_case: MemoryCheckRenderTestCase,
) -> None:
    report: RenderedReport = render_memory_check(result=test_case.result)

    assert report.text == test_case.expected_output
    assert report.fault_count == test_case.expected_fault_count
