"""Load project configuration for one named analyzer target."""

from __future__ import annotations

from pathlib import Path

from fensu.config.main.load_project_config import _load_project_config
from fensu.config.models import LoadedConfig


def load_target_project_config(*, start: Path | None, target: str | None) -> LoadedConfig:
    """Load validated project configuration using explicit target selection semantics."""

    return _load_project_config(start=start, target=target)
