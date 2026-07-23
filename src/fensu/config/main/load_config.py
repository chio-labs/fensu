"""Load a validated fensu Config from the nearest supported config source."""

from __future__ import annotations

from pathlib import Path

from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config.main.build_config import build_config
from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import Config, ConfigSource


def load_config(start: Path | None = None) -> Config:
    """Load and validate fensu config starting from a path or the current directory."""

    source: ConfigSource = locate_config(start)
    raw: dict[str, object] = dict(parse_config_source(source))
    if raw.get("rule_options"):
        return load_project_config(start).config
    return build_config(raw)
