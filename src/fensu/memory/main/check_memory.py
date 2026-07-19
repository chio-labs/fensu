"""Validate canonical Fensu Memory sources."""

from __future__ import annotations

from fensu.memory._helpers.native_operations import check
from fensu.memory._helpers.project import resolve_memory_project
from fensu.memory.models import MemoryCheckResult, MemoryProject


def check_memory(project: MemoryProject | None = None) -> MemoryCheckResult:
    """Validate enabled memory directly and publish its valid loaded corpus."""

    resolved: MemoryProject = resolve_memory_project() if project is None else project
    return check(resolved)
