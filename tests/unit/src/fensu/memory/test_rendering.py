"""Tests for deterministic Fensu Memory renderers."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.memory._helpers.graph_rendering import render_graph
from fensu.memory.main._render_memory_query import render_memory_query
from fensu.memory.main.render_memory_check import render_memory_check
from fensu.memory.main.render_memory_rebuild import render_memory_rebuild
from fensu.memory.main.render_memory_schema import render_memory_schema
from fensu.memory.main.render_memory_summary import _render_memory_overview
from fensu.memory.main.render_memory_sync import render_memory_sync
from fensu.memory.models import (
    MemoryCheckResult,
    MemoryDiagnostic,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryGraphRequest,
    MemoryGraphResult,
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
from fensu.memory.types import (
    MemoryGraphDirection,
    MemoryGraphFormat,
    MemoryGraphRelationship,
    MemoryQueryFormat,
)
from fensu.reporting.models import RenderedReport
from tests.unit.src.fensu.memory._test_types import (
    MemoryCheckRenderTestCase,
    MemoryGraphRenderTestCase,
    MemoryOverviewRenderTestCase,
    MemoryQueryRenderTestCase,
    MemoryRebuildRenderTestCase,
    MemorySchemaRenderTestCase,
    MemorySyncRenderTestCase,
)

_PROJECT: MemoryProject = MemoryProject(
    repository_root=Path("/repo"),
    database_path=Path("/repo/.fensu/memory/memory.sqlite3"),
)
_REPOSITORY_TEXT: str = str(_PROJECT.repository_root)
_DATABASE_TEXT: str = str(_PROJECT.database_path)
_QUERY_RESULT: MemoryQueryResult = MemoryQueryResult(
    columns=("value", "value"),
    types=("INTEGER", "VARCHAR"),
    rows=((1, None),),
    truncated=True,
)
_GRAPH_REQUEST: MemoryGraphRequest = MemoryGraphRequest(
    pattern="alpha",
    direction=MemoryGraphDirection.OUTBOUND,
    relationships=(MemoryGraphRelationship.LINK,),
    depth=2,
    max_nodes=2,
    max_edges=4,
    include_archived=False,
)
_GRAPH_RESULT: MemoryGraphResult = MemoryGraphResult(
    selection="exact",
    roots=("note:alpha",),
    nodes=(
        MemoryGraphNode(
            identity="note:alpha",
            artifact_kind="note",
            archive_state="active",
            repository_relative_path=".ai/knowledge/repo/notes/alpha.md",
            basename="alpha.md",
            slug="alpha",
            title="Alpha",
            depth=0,
            root=True,
        ),
        MemoryGraphNode(
            identity="note:beta",
            artifact_kind="note",
            archive_state="archived",
            repository_relative_path=".ai/_archive/knowledge/repo/notes/beta.md",
            basename="beta.md",
            slug="beta",
            title="Beta",
            depth=1,
            root=False,
        ),
    ),
    edges=(
        MemoryGraphEdge("note:alpha", 1, "link", "beta", "resolved", "note:beta", True),
        MemoryGraphEdge("note:alpha", 2, "link", "missing", "unresolved", None, False),
        MemoryGraphEdge("note:alpha", 3, "link", "duplicate", "ambiguous", None, False),
        MemoryGraphEdge("note:alpha", 4, "link", "https://example.com", "external", None, False),
    ),
    node_budget_exhausted=True,
    edge_budget_exhausted=True,
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
        MemoryGraphRenderTestCase(
            description="long graph distinguishes archived unresolved ambiguous external and cycle edges",
            result=_GRAPH_RESULT,
            request=_GRAPH_REQUEST,
            output_format=MemoryGraphFormat.LONG,
            expected_output=(
                "Memory graph\n"
                "Selection: exact (1 root(s)), outbound, depth 2\n\n"
                "Nodes (2):\n"
                "  [root] Alpha (note) <note:alpha> .ai/knowledge/repo/notes/alpha.md\n"
                "  [depth 1, archived] Beta (note) <note:beta> "
                ".ai/_archive/knowledge/repo/notes/beta.md\n\n"
                "Edges (4):\n"
                "  Alpha <note:alpha> --link--> Beta <note:beta> [resolved, archived, cycle]\n"
                "  Alpha <note:alpha> --link--> missing [unresolved]\n"
                "  Alpha <note:alpha> --link--> duplicate [ambiguous]\n"
                "  Alpha <note:alpha> --link--> https://example.com [external]\n\n"
                "Budgets: nodes 2/2 (exhausted); edges 4/4 (exhausted)\n"
            ),
        ),
        MemoryGraphRenderTestCase(
            description="JSON graph is compact deterministic and reports both exhausted budgets",
            result=_GRAPH_RESULT,
            request=_GRAPH_REQUEST,
            output_format=MemoryGraphFormat.JSON,
            expected_output=(
                '{"depth":2,"direction":"outbound","edges":['
                '{"authored_target":"beta","cycle":true,"relationship":"link",'
                '"resolution_status":"resolved","source_document_identity":"note:alpha",'
                '"source_link_ordinal":1,"target_document_identity":"note:beta"},'
                '{"authored_target":"missing","cycle":false,"relationship":"link",'
                '"resolution_status":"unresolved","source_document_identity":"note:alpha",'
                '"source_link_ordinal":2,"target_document_identity":null},'
                '{"authored_target":"duplicate","cycle":false,"relationship":"link",'
                '"resolution_status":"ambiguous","source_document_identity":"note:alpha",'
                '"source_link_ordinal":3,"target_document_identity":null},'
                '{"authored_target":"https://example.com","cycle":false,"relationship":"link",'
                '"resolution_status":"external","source_document_identity":"note:alpha",'
                '"source_link_ordinal":4,"target_document_identity":null}],'
                '"include_archived":false,"limits":{"max_edges":4,"max_nodes":2},"nodes":['
                '{"archive_state":"active","artifact_kind":"note","basename":"alpha.md",'
                '"depth":0,"identity":"note:alpha","repository_relative_path":'
                '".ai/knowledge/repo/notes/alpha.md","root":true,"slug":"alpha","title":"Alpha"},'
                '{"archive_state":"archived","artifact_kind":"note","basename":"beta.md",'
                '"depth":1,"identity":"note:beta","repository_relative_path":'
                '".ai/_archive/knowledge/repo/notes/beta.md","root":false,"slug":"beta",'
                '"title":"Beta"}],"pattern":"alpha","relationships":["link"],'
                '"roots":["note:alpha"],"selection":"exact",'
                '"truncated":{"edges":true,"nodes":true}}\n'
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_graph_result_when_rendering_then_matches_deterministic_contract(
    test_case: MemoryGraphRenderTestCase,
) -> None:
    rendered: str = render_graph(
        result=test_case.result,
        request=test_case.request,
        output_format=test_case.output_format,
        use_color=False,
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
                'SQL: fensu memory sql "SELECT * FROM memory.current_tasks"\n'
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_memory_overview_when_rendering_then_matches_compact_plan_contract(
    test_case: MemoryOverviewRenderTestCase,
) -> None:
    rendered: str = _render_memory_overview(result=test_case.result)

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
                f"Repository: {_REPOSITORY_TEXT}\n"
                f"Database: {_DATABASE_TEXT}\n"
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
                f"Repository: {_REPOSITORY_TEXT}\n"
                f"Database: {_DATABASE_TEXT}\n"
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
