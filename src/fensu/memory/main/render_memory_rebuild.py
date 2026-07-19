"""Render Fensu Memory rebuild results."""

from __future__ import annotations

from fensu.memory._helpers.human_rendering import heading
from fensu.memory.models import MemoryIndexSummary, MemoryRebuildResult


def render_memory_rebuild(*, result: MemoryRebuildResult, use_color: bool = False) -> str:
    """Render concise deterministic rebuild counts and paths."""

    summary: MemoryIndexSummary = result.summary
    return (
        f"{heading(value='Memory rebuilt', use_color=use_color)}: "
        f"documents={summary.document_count} sections={summary.section_count} "
        f"list_items={summary.list_item_count} links={summary.link_count} "
        f"tags={summary.tag_count} skill_files={summary.skill_file_count}\n"
        f"{heading(value='Diagnostics', use_color=use_color)}: "
        f"source={summary.source_diagnostic_count} corpus={summary.corpus_diagnostic_count} "
        f"graph={summary.graph_diagnostic_count}\n"
        f"{heading(value='Repository', use_color=use_color)}: "
        f"{result.project.repository_root}\n"
        f"{heading(value='Database', use_color=use_color)}: {result.project.database_path}\n"
    )
