"""Resolve enabled Strata Memory projects."""

from __future__ import annotations

from pathlib import Path

from strata.config.main.load_project_config import load_project_config
from strata.config.models import LoadedConfig
from strata.memory._helpers.bootstrap import bootstrap_memory
from strata.memory.constants import MEMORY_DATABASE_DIRECTORY, MEMORY_DATABASE_FILENAME
from strata.memory.exceptions import MemoryDisabledError
from strata.memory.models import MemoryProject


def resolve_memory_project() -> MemoryProject:
    """Resolve the configured project root and persistent memory database."""

    loaded: LoadedConfig = load_project_config(Path.cwd())
    repository_root: Path = loaded.source.path.parent.resolve()
    if not loaded.config.experimental.memory:
        raise MemoryDisabledError(
            "Strata Memory is disabled; set experimental.memory = true in the project "
            "configuration."
        )
    bootstrap_memory(repository_root)
    database_path: Path = repository_root / MEMORY_DATABASE_DIRECTORY / MEMORY_DATABASE_FILENAME
    return MemoryProject(repository_root=repository_root, database_path=database_path)
