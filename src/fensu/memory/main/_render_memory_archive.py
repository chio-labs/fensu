"""Render explicit Fensu Memory archive results internally."""

from __future__ import annotations

from fensu.memory._helpers.human_rendering import heading
from fensu.memory.models import MemoryArchiveResult


def render_memory_archive(*, result: MemoryArchiveResult, use_color: bool = False) -> str:
    """Render deterministic archive moves and resulting index counts."""

    if not result.moves:
        return f"{heading(value='Memory archive', use_color=use_color)}: no eligible sources\n"
    lines: list[str] = [f"{heading(value='Memory archived', use_color=use_color)}:"]
    lines.extend(f"  {entry.source} -> {entry.destination}" for entry in result.moves)
    if result.sync is not None:
        lines.append(
            f"Index: documents={result.sync.document_count} "
            f"sections={result.sync.section_count} links={result.sync.link_count}"
        )
    return "\n".join(lines) + "\n"
