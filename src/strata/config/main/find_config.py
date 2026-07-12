"""Find optional Strata configuration for commands with standalone modes."""

from __future__ import annotations

from pathlib import Path

from strata.config.exceptions import ConfigError
from strata.config.helpers.discovery import locate_config
from strata.config.models import ConfigSource


def find_config_source(start: Path) -> ConfigSource | None:
    """Return the nearest Strata config, or none when the project has no config."""

    try:
        return locate_config(start)
    except ConfigError as error:
        if str(error).startswith("No strata config found"):
            return None
        raise
