"""Validated and transactional filesystem execution for initialization."""

from __future__ import annotations

import json
import os
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from strata.config.exceptions import ConfigError
from strata.config.main.build_config import build_config
from strata.config.models import Config
from strata.discovery.main.build_project_layout import build_project_layout
from strata.discovery.models import ProjectLayout, RepoRoot
from strata.scaffolding.constants import (
    ADOPTION_LINK,
    CONFIG_FILE_NAME,
    CONFIG_TEMP_PREFIX,
    CONFIG_TEMP_SUFFIX,
    FULL_SELECT,
    GRADUAL_SELECT,
    PACKAGE_MARKER_FILE_NAME,
    PYTHON_FILE_SUFFIX,
)
from strata.scaffolding.exceptions import InitError
from strata.scaffolding.models import InitExecution, InitPlan
from strata.scaffolding.types import AdoptionMode


def render_config(*, plan: InitPlan) -> str:
    """Render the minimal deterministic TOML configuration."""

    lines: list[str] = [
        f"roots = {_toml_array(values=plan.roots)}",
        f"tests = {_toml_array(values=plan.tests)}",
    ]
    if plan.tooling:
        lines.append(f"tooling = {_toml_array(values=plan.tooling)}")
    if plan.adoption is AdoptionMode.GRADUAL:
        lines.append(f"# Adoption guide: https://{ADOPTION_LINK}")
    selected: tuple[str, ...] = (
        FULL_SELECT if plan.adoption is AdoptionMode.FULL else GRADUAL_SELECT
    )
    lines.append(f"select = {_toml_array(values=selected)}")
    return "\n".join(lines) + "\n"


def build_rendered_config(*, text: str) -> Config:
    """Round-trip rendered TOML through the public in-memory config builder."""

    raw: object = tomllib.loads(text)
    return build_config(cast("Mapping[str, object]", raw))


def execute_init_plan(*, repository: Path, plan: InitPlan) -> tuple[Config, InitExecution]:
    """Validate and write a config, scaffolding empty roots transactionally."""

    text: str = render_config(plan=plan)
    config: Config = build_rendered_config(text=text)
    _ensure_config_absent(repository=repository)
    if plan.project_name is None:
        _validate_layout(repository=repository, config=config)
        _validate_selected_scope_symlinks(repository=repository, config=config)
        _atomic_write_config(repository=repository, text=text)
        return config, InitExecution(config_path=CONFIG_FILE_NAME, created_paths=())
    created: tuple[Path, ...] = ()
    logical_paths: tuple[str, ...] = (
        f"src/{plan.project_name}/__init__.py",
        "tests/.gitkeep",
    )
    try:
        for value in logical_paths:
            created = _create_empty_file(repository=repository, relative=value, created=created)
        _validate_layout(repository=repository, config=config)
        _validate_selected_scope_symlinks(repository=repository, config=config)
        _atomic_write_config(repository=repository, text=text)
    except (ConfigError, InitError, OSError):
        _rollback(paths=created)
        raise
    return config, InitExecution(config_path=CONFIG_FILE_NAME, created_paths=logical_paths)


def _validate_layout(*, repository: Path, config: Config) -> None:
    layout: ProjectLayout = build_project_layout(
        config=config, repo_root=RepoRoot(path=repository.resolve())
    )
    _ = layout


def _create_empty_file(
    *, repository: Path, relative: str, created: tuple[Path, ...]
) -> tuple[Path, ...]:
    path: Path = repository / relative
    _validate_scaffold_path(repository=repository, path=path)
    missing_parents: list[Path] = []
    parent: Path = path.parent
    while parent != repository and not parent.exists():
        missing_parents.append(parent)
        parent = parent.parent
    for directory in reversed(missing_parents):
        directory.mkdir()
        created = (*created, directory)
    if path.exists() and not path.is_file():
        raise InitError(f"Scaffold file path is not a file: {path}")
    if not path.exists():
        path.touch()
        created = (*created, path)
    return created


def _atomic_write_config(*, repository: Path, text: str) -> None:
    _ensure_config_absent(repository=repository)
    descriptor: int
    temp_text: str
    descriptor, temp_text = tempfile.mkstemp(
        dir=repository,
        prefix=CONFIG_TEMP_PREFIX,
        suffix=CONFIG_TEMP_SUFFIX,
        text=True,
    )
    temp_path: Path = Path(temp_text)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            _ = file.write(text)
            file.flush()
            os.fsync(file.fileno())
        _ensure_config_absent(repository=repository)
        try:
            os.link(
                temp_path,
                repository / CONFIG_FILE_NAME,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise InitError(
                "Refusing to replace configuration path created concurrently: "
                f"{repository / CONFIG_FILE_NAME}"
            ) from error
    except (InitError, OSError):
        if temp_path.is_symlink() or temp_path.exists():
            temp_path.unlink()
        raise
    try:
        temp_path.unlink()
    except OSError:
        pass


def _ensure_config_absent(*, repository: Path) -> None:
    path: Path = repository / CONFIG_FILE_NAME
    if path.is_symlink() or path.exists():
        raise InitError(f"Refusing to replace existing configuration path: {path}")


def _validate_selected_scope_symlinks(*, repository: Path, config: Config) -> None:
    values: tuple[str, ...] = (*config.roots, *config.tests, *config.tooling)
    for value in values:
        scope: Path = repository / value
        _validate_scope_path(repository=repository, scope=scope, value=value)
        if not scope.is_dir():
            continue
        for current_text, directories, files in os.walk(scope, followlinks=False):
            current: Path = Path(current_text)
            names: tuple[str, ...] = (*directories, *files)
            for name in names:
                candidate: Path = current / name
                if candidate.is_symlink() and (
                    candidate.suffix == PYTHON_FILE_SUFFIX
                    or candidate.name == PACKAGE_MARKER_FILE_NAME
                ):
                    raise InitError(f"Selected scope contains a symlinked Python path: {candidate}")
            directories[:] = [name for name in directories if not (current / name).is_symlink()]


def _validate_scope_path(*, repository: Path, scope: Path, value: str) -> None:
    current: Path = repository
    for part in scope.relative_to(repository).parts:
        current = current / part
        if current.is_symlink():
            raise InitError(f"Selected scope traverses a symlink: {value} ({current})")


def _validate_scaffold_path(*, repository: Path, path: Path) -> None:
    relative: Path = path.relative_to(repository)
    current: Path = repository
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise InitError(f"Refusing to scaffold through symlink path: {current}")


def _rollback(*, paths: tuple[Path, ...]) -> None:
    for path in reversed(paths):
        if path.is_dir():
            path.rmdir()
        elif path.exists():
            path.unlink()


def _toml_array(*, values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"
