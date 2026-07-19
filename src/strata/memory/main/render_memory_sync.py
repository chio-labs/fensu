"""Render Strata Memory synchronization results."""

from __future__ import annotations

from strata.memory._helpers.human_rendering import heading
from strata.memory.models import MemorySyncResult, MemorySyncSummary


def render_memory_sync(
    *, result: MemorySyncResult, compact: bool = False, use_color: bool = False
) -> str:
    """Render concise deterministic synchronization counts and paths."""

    sync: MemorySyncSummary = result.sync
    if compact:
        return _compact(sync=sync, use_color=use_color)
    rebuilt: str = "yes" if sync.rebuilt else "no"
    return (
        f"{heading(value='Memory sync', use_color=use_color)}: "
        f"added={sync.added_count} changed={sync.changed_count} moved={sync.moved_count} "
        f"removed={sync.removed_count} unchanged={sync.unchanged_count} rebuilt={rebuilt}\n"
        f"{heading(value='Index', use_color=use_color)}: "
        f"documents={sync.document_count} sections={sync.section_count} "
        f"links={sync.link_count}\n"
        f"{heading(value='Repository', use_color=use_color)}: "
        f"{result.project.repository_root}\n"
        f"{heading(value='Database', use_color=use_color)}: {result.project.database_path}\n"
    )


def _compact(*, sync: MemorySyncSummary, use_color: bool) -> str:
    if not sync.changed:
        return ""
    return (
        f"{heading(value='Memory synced', use_color=use_color)}: "
        f"+{sync.added_count} ~{sync.changed_count} >{sync.moved_count} -{sync.removed_count}\n"
    )
