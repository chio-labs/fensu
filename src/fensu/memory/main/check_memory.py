"""Validate canonical Fensu Memory sources."""

from __future__ import annotations

from fensu.memory._helpers.native_operations import check
from fensu.memory.models import MemoryCheckResult, MemoryProject


def check_memory(project: MemoryProject) -> MemoryCheckResult:
    """Validate configured memory and publish its valid loaded corpus."""

    return check(project)
