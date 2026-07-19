"""Archive canonical Fensu Memory sources internally."""

from __future__ import annotations

from pathlib import Path

from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import LoadedConfig
from fensu.memory._helpers.native_operations import archive
from fensu.memory._helpers.project import resolve_memory_project
from fensu.memory.models import MemoryArchiveResult, MemoryProject


def archive_memory(*, paths: tuple[str, ...], confirmed: bool) -> MemoryArchiveResult:
    """Archive explicit sources or eligible terminal tasks and synchronize memory."""

    project: MemoryProject = resolve_memory_project()
    loaded: LoadedConfig = load_project_config(Path.cwd())
    return archive(
        project=project,
        requested_paths=paths,
        archive_after_days=loaded.config.memory.tasks.archive_after_days,
        confirmed=confirmed,
    )
