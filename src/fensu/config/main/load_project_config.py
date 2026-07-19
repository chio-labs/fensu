"""Load validated configuration with its authoritative source location."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fensu.config._helpers.discovery import locate_config
from fensu.config._helpers.parse import parse_config_source
from fensu.config.main.build_config import build_config
from fensu.config.models import ConfigSource, LoadedConfig


def load_project_config(start: Path | None = None) -> LoadedConfig:
    """Load validated config together with its authoritative source location."""

    source: ConfigSource = locate_config(start)
    raw_config: Mapping[str, object] = parse_config_source(source)
    return LoadedConfig(config=build_config(raw_config), source=source)
