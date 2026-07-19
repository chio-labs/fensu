"""Resolve enabled Fensu Memory projects."""

from __future__ import annotations

from pathlib import Path

from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import LoadedConfig
from fensu.memory._helpers.bootstrap import bootstrap_memory
from fensu.memory.constants import MEMORY_DATABASE_DIRECTORY, MEMORY_DATABASE_FILENAME
from fensu.memory.exceptions import MemoryDisabledError
from fensu.memory.models import MemoryProject


def resolve_memory_project() -> MemoryProject:
    """Resolve the configured project root and persistent memory database."""

    loaded: LoadedConfig = load_project_config(Path.cwd())
    repository_root: Path = loaded.source.path.parent.resolve()
    if not loaded.config.experimental.memory:
        raise MemoryDisabledError(
            "Fensu Memory is disabled; set experimental.memory = true in the project configuration."
        )
    bootstrap_memory(repository_root)
    database_path: Path = repository_root / MEMORY_DATABASE_DIRECTORY / MEMORY_DATABASE_FILENAME
    return MemoryProject(repository_root=repository_root, database_path=database_path)
