"""Load a validated fensu Config from the nearest supported config source."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config._helpers.validate import select_config_target
from fensu.config.main.build_config import build_config
from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import Config, ConfigSource


def load_config(start: Path | None = None) -> Config:
    """Load and validate fensu config starting from a path or the current directory."""

    source: ConfigSource = locate_config(start)
    parsed: dict[str, object] = dict(parse_config_source(source))
    raw, target_name, analyzer, target_root = select_config_target(raw=parsed, target=None)
    if raw.get("rule_options"):
        return load_project_config(start).config
    return replace(
        build_config(raw),
        analyzer=analyzer,
        target=target_name,
        target_root=target_root,
    )
