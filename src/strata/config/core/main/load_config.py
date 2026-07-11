"""Load a validated strata Config from the nearest supported config source."""

from __future__ import annotations

from pathlib import Path

from strata.config.core.main.load_project_config import load_project_config
from strata.config.core.models import Config


def load_config(start: Path | None = None) -> Config:
    """Load and validate strata config starting from a path or the current directory."""

    return load_project_config(start).config
