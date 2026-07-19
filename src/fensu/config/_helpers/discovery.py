"""Discover the config source for a repository."""

from __future__ import annotations

import tomllib
from pathlib import Path

from fensu.config.exceptions import ConfigError
from fensu.config.models import ConfigSource
from fensu.config.types import ConfigSourceKind


def locate_config(start: Path | None = None) -> ConfigSource:
    """Find the nearest fensu.toml or pyproject [tool.fensu] config source."""

    current: Path = Path.cwd() if start is None else start.resolve()
    directory: Path = current if current.is_dir() else current.parent
    for candidate_directory in (directory, *directory.parents):
        fensu_toml: Path = candidate_directory / "fensu.toml"
        if fensu_toml.is_file():
            return ConfigSource(path=fensu_toml, kind=ConfigSourceKind.FENSU_TOML)
        pyproject: Path = candidate_directory / "pyproject.toml"
        if pyproject.is_file() and _pyproject_has_fensu_config(pyproject):
            return ConfigSource(path=pyproject, kind=ConfigSourceKind.PYPROJECT)
    raise ConfigError(
        "No fensu config found; create fensu.toml or [tool.fensu]. Run 'fensu init' to create one."
    )


def _pyproject_has_fensu_config(path: Path) -> bool:
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
    return isinstance(tool.get("fensu"), dict)
