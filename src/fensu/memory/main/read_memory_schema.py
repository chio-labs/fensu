"""Read public Fensu Memory schema metadata."""

from __future__ import annotations

from fensu.memory._helpers.native_operations import relation_schema, schema_overview
from fensu.memory._helpers.project import resolve_memory_project
from fensu.memory.models import (
    MemoryProject,
    MemoryRelationSchema,
    MemorySchema,
    MemorySchemaResult,
)


def read_memory_schema(relation: str | None = None) -> MemorySchemaResult:
    """Return all public relations or focused metadata for one relation."""

    project: MemoryProject = resolve_memory_project()
    if relation is None:
        schema: MemorySchema = schema_overview()
        return MemorySchemaResult(project=project, schema=schema, relation=None)
    focused: MemoryRelationSchema = relation_schema(relation)
    return MemorySchemaResult(project=project, schema=None, relation=focused)
