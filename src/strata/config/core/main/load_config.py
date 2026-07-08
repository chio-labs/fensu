"""Load a validated strata Config from the nearest supported config source."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from strata.config.core.helpers.defaults import build_config
from strata.config.core.helpers.discovery import locate_config
from strata.config.core.helpers.parse import parse_config_source
from strata.config.core.helpers.validate import validate_config
from strata.config.core.models import Config, ConfigSource


def load_config(start: Path | None = None) -> Config:
    """Load and validate strata config starting from a path or the current directory."""

    source: ConfigSource = locate_config(start)
    raw_config: Mapping[str, object] = parse_config_source(source)
    validate_config(raw_config)
    return build_config(raw_config)
