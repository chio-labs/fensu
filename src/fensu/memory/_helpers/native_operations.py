"""Typed conversion at the private native memory boundary."""

from __future__ import annotations

import fensu._native as _native
from fensu.memory.exceptions import MemoryOperationError
from fensu.memory.models import (
    MemoryCheckResult,
    MemoryDiagnostic,
    MemoryIndexSummary,
    MemoryProject,
)


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
