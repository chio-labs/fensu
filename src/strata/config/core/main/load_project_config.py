"""Load validated configuration with its authoritative source location."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from strata.config.core.helpers.defaults import build_config
from strata.config.core.helpers.discovery import locate_config
from strata.config.core.helpers.parse import parse_config_source
from strata.config.core.helpers.validate import validate_config
from strata.config.core.models import ConfigSource, LoadedConfig


def load_project_config(start: Path | None = None) -> LoadedConfig:
    """Load validated config together with its authoritative source location."""

    source: ConfigSource = locate_config(start)
    raw_config: Mapping[str, object] = parse_config_source(source)
    validate_config(raw_config)
    return LoadedConfig(config=build_config(raw_config), source=source)
