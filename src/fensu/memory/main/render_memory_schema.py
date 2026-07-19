"""Render public Fensu Memory schema metadata."""

from __future__ import annotations

from fensu.memory._helpers.human_rendering import column_lines, heading, relation_lines
from fensu.memory.constants import RELATION_KIND_TABLE, RELATION_KIND_VIEW
from fensu.memory.exceptions import MemoryOperationError
from fensu.memory.models import (
    MemoryRelationSchema,
    MemorySchema,
    MemorySchemaRelation,
    MemorySchemaResult,
)


def render_memory_schema(*, result: MemorySchemaResult, use_color: bool = False) -> str:
    """Render grouped schema metadata or one focused relation."""

    if result.relation is not None:
        return _focused(relation=result.relation, use_color=use_color)
    if result.schema is None:
        raise MemoryOperationError("Memory schema metadata was unavailable.")
    return _overview(schema=result.schema, use_color=use_color)


def _overview(*, schema: MemorySchema, use_color: bool) -> str:
    tables: tuple[MemorySchemaRelation, ...] = tuple(
        relation for relation in schema.relations if relation.kind == RELATION_KIND_TABLE
    )
    views: tuple[MemorySchemaRelation, ...] = tuple(
        relation for relation in schema.relations if relation.kind == RELATION_KIND_VIEW
    )
    lines: list[str] = [
        f"Memory schema {schema.schema_version} (parser contract {schema.parser_contract_version})",
        "",
        f"{heading(value='Stored tables', use_color=use_color)}:",
        *relation_lines(tables),
        "",
        f"{heading(value='Convenience views', use_color=use_color)}:",
        *relation_lines(views),
    ]
    return "\n".join(lines) + "\n"


def _focused(*, relation: MemoryRelationSchema, use_color: bool) -> str:
    lines: list[str] = [
        f"{heading(value=relation.name, use_color=use_color)} ({relation.kind})",
        relation.comment,
        "",
        *column_lines(relation.columns),
    ]
    return "\n".join(lines) + "\n"
