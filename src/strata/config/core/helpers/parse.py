"""Parse the selected TOML config source into a raw mapping."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from typing import cast

from strata.config.core.exceptions import ConfigError
from strata.config.core.models import ConfigSource
from strata.config.core.types import ConfigSourceKind


def parse_config_source(source: ConfigSource) -> Mapping[str, object]:
    """Parse strata.toml directly or extract [tool.strata] from pyproject.toml."""

    try:
        with source.path.open("rb") as file:
            data: object = tomllib.load(file)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Could not parse {source.path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"Config source {source.path} did not contain a TOML table.")
    if source.kind is ConfigSourceKind.STRATA_TOML:
        return data
    return _extract_pyproject_config(data=data, path=str(source.path))


def _extract_pyproject_config(*, data: Mapping[str, object], path: str) -> Mapping[str, object]:
    tool: object = data.get("tool")
    if not isinstance(tool, dict):
        raise ConfigError(f"{path} does not contain [tool.strata].")
    config: object = tool.get("strata")
    if not isinstance(config, dict):
        raise ConfigError(f"{path} does not contain [tool.strata].")
    return cast("Mapping[str, object]", config)
