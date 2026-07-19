"""Load a validated fensu Config from the nearest supported config source."""

from __future__ import annotations

from pathlib import Path

from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import Config


def load_config(start: Path | None = None) -> Config:
    """Load and validate fensu config starting from a path or the current directory."""

    return load_project_config(start).config
