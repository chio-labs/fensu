"""Render the compact Strata Memory plan overview."""

from __future__ import annotations

from strata.memory._helpers.human_rendering import heading
from strata.memory.models import MemoryOverview, MemoryOverviewResult


def render_memory_overview(*, result: MemoryOverviewResult, use_color: bool = False) -> str:
    """Render task, knowledge, archive, index, and SQL guidance."""

    overview: MemoryOverview = result.overview
    return (
        f"{heading(value='Tasks', use_color=use_color)}: "
        f"{overview.not_started_task_count} not started, "
        f"{overview.in_progress_task_count} in progress, "
        f"{overview.completed_task_count} completed, "
        f"{overview.cancelled_task_count} cancelled, "
        f"{overview.superseded_task_count} superseded\n"
        f"{heading(value='Knowledge', use_color=use_color)}: "
        f"{overview.active_note_count} notes, {overview.active_decision_count} decisions, "
        f"{overview.active_skill_count} skills\n"
        f"{heading(value='Archive', use_color=use_color)}: "
        f"{overview.archived_task_count} tasks, "
        f"{overview.archived_knowledge_count} knowledge\n"
        f"{heading(value='Index', use_color=use_color)}: "
        f"{overview.document_count} documents, {overview.section_count} sections\n"
        'SQL: strata memory sql "SELECT * FROM memory.current_tasks"\n'
    )
