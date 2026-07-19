"""Archive and render canonical Fensu Memory sources."""

from __future__ import annotations

from fensu.memory.main._archive_memory import archive_memory
from fensu.memory.main._render_memory_archive import render_memory_archive
from fensu.memory.models import MemoryArchiveResult


def run_memory_archive(*, paths: tuple[str, ...], confirmed: bool, use_color: bool = False) -> str:
    """Return deterministic output for one archive command."""

    result: MemoryArchiveResult = archive_memory(paths=paths, confirmed=confirmed)
    return render_memory_archive(result=result, use_color=use_color)
