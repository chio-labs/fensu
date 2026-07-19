"""Find optional Fensu configuration for commands with standalone modes."""

from __future__ import annotations

from pathlib import Path

from fensu.config._helpers.discovery import locate_config
from fensu.config.exceptions import ConfigError
from fensu.config.models import ConfigSource


def find_config_source(start: Path) -> ConfigSource | None:
    """Return the nearest Fensu config, or none when the project has no config."""

    try:
        return locate_config(start)
    except ConfigError as error:
        if str(error).startswith("No fensu config found"):
            return None
        raise
