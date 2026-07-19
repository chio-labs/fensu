"""Discover the config source for a repository."""

from __future__ import annotations

import tomllib
from pathlib import Path

from strata.config.exceptions import ConfigError
from strata.config.models import ConfigSource
from strata.config.types import ConfigSourceKind


def locate_config(start: Path | None = None) -> ConfigSource:
    """Find the nearest strata.toml or pyproject [tool.strata] config source."""

    current: Path = Path.cwd() if start is None else start.resolve()
    directory: Path = current if current.is_dir() else current.parent
    for candidate_directory in (directory, *directory.parents):
        strata_toml: Path = candidate_directory / "strata.toml"
        if strata_toml.is_file():
            return ConfigSource(path=strata_toml, kind=ConfigSourceKind.STRATA_TOML)
        pyproject: Path = candidate_directory / "pyproject.toml"
        if pyproject.is_file() and _pyproject_has_strata_config(pyproject):
            return ConfigSource(path=pyproject, kind=ConfigSourceKind.PYPROJECT)
    raise ConfigError(
        "No strata config found; create strata.toml or [tool.strata]. "
        "Run 'strata init' to create one."
    )


def _pyproject_has_strata_config(path: Path) -> bool:
    try:
        with path.open("rb") as file:
            data: object = tomllib.load(file)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Could not parse {path}: {error}") from error
    if not isinstance(data, dict):
        return False
    tool: object = data.get("tool")
    if not isinstance(tool, dict):
        return False
    return isinstance(tool.get("strata"), dict)
