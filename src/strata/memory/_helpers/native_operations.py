"""Typed conversion at the private native memory boundary."""

from __future__ import annotations

from pathlib import Path

import strata._native as _native
from strata.memory.constants import MEMORY_SCHEMA_PREFIX
from strata.memory.exceptions import MemoryOperationError, MemoryRelationNotFoundError
from strata.memory.models import (
    MemoryArchiveMove,
    MemoryArchiveResult,
    MemoryCheckResult,
    MemoryDiagnostic,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryGraphRequest,
    MemoryGraphResult,
    MemoryIndexSummary,
    MemoryOverview,
    MemoryProject,
    MemoryQueryResult,
    MemoryRelationSchema,
    MemorySchema,
    MemorySchemaColumn,
    MemorySchemaRelation,
    MemorySyncSummary,
)


def synchronize(project: MemoryProject) -> MemorySyncSummary:
    """Synchronize repository memory sources through the native engine."""

    try:
        values: tuple[int, int, int, int, int, bool, bool, int, int, int] = _native.memory_sync(
            project.repository_root, project.database_path
        )
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory sync failed: {error}") from error
    return MemorySyncSummary(*values)


def rebuild(project: MemoryProject) -> MemoryIndexSummary:
    """Rebuild the persistent memory index through the native engine."""

    try:
        values: tuple[int, int, int, int, int, int, int, int, int] = _native.memory_rebuild(
            project.repository_root, project.database_path
        )
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory rebuild failed: {error}") from error
    return MemoryIndexSummary(*values)


def check(project: MemoryProject) -> MemoryCheckResult:
    """Validate canonical sources and publish the valid loaded corpus."""

    try:
        raw_diagnostics, raw_published = _native.memory_check(
            project.repository_root, project.database_path
        )
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory check failed: {error}") from error
    diagnostics: tuple[MemoryDiagnostic, ...] = tuple(
        MemoryDiagnostic(*values) for values in raw_diagnostics
    )
    published: MemoryIndexSummary | None = (
        None if raw_published is None else MemoryIndexSummary(*raw_published)
    )
    return MemoryCheckResult(project=project, diagnostics=diagnostics, published=published)


def archive(
    *,
    project: MemoryProject,
    requested_paths: tuple[str, ...],
    archive_after_days: int,
    confirmed: bool,
) -> MemoryArchiveResult:
    """Archive canonical sources and synchronize through the native engine."""

    try:
        raw_moves, raw_sync = _native.memory_archive(
            project.repository_root,
            project.database_path,
            [Path(path) for path in requested_paths],
            archive_after_days,
            confirmed,
        )
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory archive failed: {error}") from error
    moves: tuple[MemoryArchiveMove, ...] = tuple(
        MemoryArchiveMove(source=source, destination=destination)
        for source, destination in raw_moves
    )
    sync: MemorySyncSummary | None = None if raw_sync is None else MemorySyncSummary(*raw_sync)
    return MemoryArchiveResult(project=project, moves=moves, sync=sync)


def overview(project: MemoryProject) -> MemoryOverview:
    """Read current memory counts through the native engine."""

    try:
        values: tuple[int, int, int, int, int, int, int, int, int, int, int, int] = (
            _native.memory_overview(project.database_path)
        )
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory overview failed: {error}") from error
    return MemoryOverview(*values)


def schema_overview() -> MemorySchema:
    """Read compiled public schema metadata through the native engine."""

    try:
        schema_version, parser_version, raw_relations = _native.memory_schema()
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory schema failed: {error}") from error
    relations: tuple[MemorySchemaRelation, ...] = tuple(
        MemorySchemaRelation(name=name, kind=kind, comment=comment)
        for name, kind, comment in raw_relations
    )
    return MemorySchema(
        schema_version=schema_version,
        parser_contract_version=parser_version,
        relations=relations,
    )


def relation_schema(name: str) -> MemoryRelationSchema:
    """Read compiled metadata for one qualified public relation."""

    qualified: str = name if name.startswith(MEMORY_SCHEMA_PREFIX) else MEMORY_SCHEMA_PREFIX + name
    try:
        raw_relation: tuple[str, str, str, tuple[tuple[str, str, bool, str], ...]] | None = (
            _native.memory_relation_schema(qualified)
        )
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory schema failed: {error}") from error
    if raw_relation is None:
        raise MemoryRelationNotFoundError(f"Unknown memory relation: {qualified}")
    relation_name, kind, comment, raw_columns = raw_relation
    columns: tuple[MemorySchemaColumn, ...] = tuple(
        MemorySchemaColumn(
            name=column_name,
            data_type=data_type,
            nullable=nullable,
            comment=column_comment,
        )
        for column_name, data_type, nullable, column_comment in raw_columns
    )
    return MemoryRelationSchema(
        name=relation_name,
        kind=kind,
        comment=comment,
        columns=columns,
    )


def query(*, project: MemoryProject, sql: str, limit: int) -> MemoryQueryResult:
    """Run one bounded read-only query through the native engine."""

    try:
        columns, types, rows, truncated = _native.memory_query(project.database_path, sql, limit)
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory query failed: {error}") from error
    return MemoryQueryResult(columns=columns, types=types, rows=rows, truncated=truncated)


def graph(*, project: MemoryProject, request: MemoryGraphRequest) -> MemoryGraphResult:
    """Run one bounded graph query through the native engine."""

    try:
        selection, roots, raw_nodes, raw_edges, node_exhausted, edge_exhausted = (
            _native.memory_graph(
                project.database_path,
                (
                    request.pattern,
                    request.direction,
                    [str(value) for value in request.relationships],
                    request.depth,
                    request.max_nodes,
                    request.max_edges,
                    request.include_archived,
                ),
            )
        )
    except RuntimeError as error:
        raise MemoryOperationError(f"Memory graph failed: {error}") from error
    nodes: tuple[MemoryGraphNode, ...] = tuple(MemoryGraphNode(*values) for values in raw_nodes)
    edges: tuple[MemoryGraphEdge, ...] = tuple(MemoryGraphEdge(*values) for values in raw_edges)
    return MemoryGraphResult(
        selection=selection,
        roots=roots,
        nodes=nodes,
        edges=edges,
        node_budget_exhausted=node_exhausted,
        edge_budget_exhausted=edge_exhausted,
    )
