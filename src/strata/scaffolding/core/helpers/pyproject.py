"""Extract deterministic layout signals from standard pyproject tables."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from strata.scaffolding.core.constants import (
    PACKAGE_MARKER_FILE_NAME,
    PARENT_PATH_PART,
    PYPROJECT_FILE_NAME,
    SOURCE_CONTAINER_NAMES,
    WORKSPACE_WILDCARD,
)
from strata.scaffolding.core.exceptions import PyprojectParseError
from strata.scaffolding.core.helpers.filesystem import package_children
from strata.scaffolding.core.types import CandidateInput, CandidateProvenance


def load_pyproject(*, repository: Path) -> Mapping[str, object]:
    """Load root packaging metadata, raising a scaffolding error for invalid TOML."""

    path: Path = repository / PYPROJECT_FILE_NAME
    if not path.is_file():
        return {}
    return _load_toml(path=path, display_path=PYPROJECT_FILE_NAME)


def metadata_root_inputs(
    *, repository: Path, data: Mapping[str, object]
) -> tuple[CandidateInput, ...]:
    """Return root signals in the packaging and neighboring-tool order from the plan."""

    inputs: list[CandidateInput] = []
    inputs.extend(_hatch_inputs(project_root=repository, data=data))
    inputs.extend(_setuptools_inputs(repository=repository, project_root=repository, data=data))
    inputs.extend(_poetry_inputs(project_root=repository, data=data))
    inputs.extend(_flit_inputs(repository=repository, project_root=repository, data=data))
    inputs.extend(_workspace_inputs(repository=repository, data=data))
    inputs.extend(_project_name_inputs(repository=repository, project_root=repository, data=data))
    inputs.extend(_ruff_inputs(repository=repository, project_root=repository, data=data))
    return tuple(inputs)


def pytest_inputs(*, repository: Path, data: Mapping[str, object]) -> tuple[CandidateInput, ...]:
    """Return configured pytest testpaths in declaration order."""

    pytest: Mapping[str, object] = _table(data=data, keys=("tool", "pytest", "ini_options"))
    values: tuple[str, ...] = _strings(value=pytest.get("testpaths"))
    return tuple((repository / value, CandidateProvenance.PYTEST_TESTPATHS) for value in values)


def _hatch_inputs(*, project_root: Path, data: Mapping[str, object]) -> tuple[CandidateInput, ...]:
    wheel: Mapping[str, object] = _table(
        data=data, keys=("tool", "hatch", "build", "targets", "wheel")
    )
    return tuple(
        (project_root / value, CandidateProvenance.HATCH_PACKAGES)
        for value in _strings(value=wheel.get("packages"))
    )


def _setuptools_inputs(
    *, repository: Path, project_root: Path, data: Mapping[str, object]
) -> tuple[CandidateInput, ...]:
    setuptools: Mapping[str, object] = _table(data=data, keys=("tool", "setuptools"))
    find: Mapping[str, object] = _mapping(
        value=_mapping(value=setuptools.get("packages")).get("find")
    )
    inputs: list[CandidateInput] = []
    for value in _strings(value=find.get("where")):
        container: Path | None = _safe_directory(repository=repository, path=project_root / value)
        if container is not None:
            inputs.extend(
                (path, CandidateProvenance.SETUPTOOLS_FIND)
                for path in package_children(container=container)
            )
    package_dir: Mapping[str, object] = _mapping(value=setuptools.get("package-dir"))
    for package_name, value in package_dir.items():
        if not isinstance(value, str):
            continue
        path: Path = project_root / value
        if package_name:
            inputs.append((path, CandidateProvenance.SETUPTOOLS_PACKAGE_DIR))
            continue
        container = _safe_directory(repository=repository, path=path)
        if container is not None:
            inputs.extend(
                (child, CandidateProvenance.SETUPTOOLS_PACKAGE_DIR)
                for child in package_children(container=container)
            )
    return tuple(inputs)


def _poetry_inputs(*, project_root: Path, data: Mapping[str, object]) -> tuple[CandidateInput, ...]:
    poetry: Mapping[str, object] = _table(data=data, keys=("tool", "poetry"))
    inputs: list[CandidateInput] = []
    packages: object = poetry.get("packages")
    if not isinstance(packages, list):
        return ()
    for item in packages:
        package: Mapping[str, object] = _mapping(value=item)
        include: object = package.get("include")
        source: object = package.get("from", ".")
        if isinstance(include, str) and isinstance(source, str):
            inputs.append((project_root / source / include, CandidateProvenance.POETRY_PACKAGES))
    return tuple(inputs)


def _flit_inputs(
    *, repository: Path, project_root: Path, data: Mapping[str, object]
) -> tuple[CandidateInput, ...]:
    module: Mapping[str, object] = _table(data=data, keys=("tool", "flit", "module"))
    name: object = module.get("name")
    if not isinstance(name, str) or not name:
        return ()
    relative: Path = Path(*name.split("."))
    paths: list[Path] = [project_root / relative]
    paths.extend(project_root / container / relative for container in SOURCE_CONTAINER_NAMES)
    return tuple(
        (path, CandidateProvenance.FLIT_MODULE)
        for path in paths
        if _safe_directory(repository=repository, path=path) is not None
    )


def _workspace_inputs(
    *, repository: Path, data: Mapping[str, object]
) -> tuple[CandidateInput, ...]:
    workspace: Mapping[str, object] = _table(data=data, keys=("tool", "uv", "workspace"))
    inputs: list[CandidateInput] = []
    for value in _strings(value=workspace.get("members")):
        for member in _workspace_members(repository=repository, value=value):
            inputs.extend(_workspace_package_inputs(repository=repository, member=member))
    return tuple(inputs)


def _workspace_package_inputs(*, repository: Path, member: Path) -> tuple[CandidateInput, ...]:
    paths: list[Path] = []
    marker: Path = member / PACKAGE_MARKER_FILE_NAME
    if not marker.is_symlink() and marker.is_file():
        paths.append(member)
    paths.extend(package_children(container=member))
    for name in SOURCE_CONTAINER_NAMES:
        paths.extend(package_children(container=member / name))
    pyproject: Path = member / PYPROJECT_FILE_NAME
    if pyproject.is_file():
        display_path: str = pyproject.relative_to(repository).as_posix()
        data: Mapping[str, object] = _load_toml(path=pyproject, display_path=display_path)
        nested: tuple[CandidateInput, ...] = (
            *_hatch_inputs(project_root=member, data=data),
            *_setuptools_inputs(repository=repository, project_root=member, data=data),
            *_poetry_inputs(project_root=member, data=data),
            *_flit_inputs(repository=repository, project_root=member, data=data),
            *_project_name_inputs(repository=repository, project_root=member, data=data),
        )
        paths.extend(path for path, _ in nested)
    unique_paths: tuple[Path, ...] = tuple(dict.fromkeys(paths))
    return tuple((path, CandidateProvenance.UV_WORKSPACE) for path in unique_paths)


def _project_name_inputs(
    *, repository: Path, project_root: Path, data: Mapping[str, object]
) -> tuple[CandidateInput, ...]:
    project: Mapping[str, object] = _mapping(value=data.get("project"))
    name: object = project.get("name")
    if not isinstance(name, str) or not name:
        return ()
    normalized: str = re.sub(r"[-_.]+", "_", name).lower()
    paths: list[Path] = [project_root / normalized]
    paths.extend(project_root / container / normalized for container in SOURCE_CONTAINER_NAMES)
    packages: Path = project_root / "packages"
    if packages.is_dir() and not packages.is_symlink():
        for member in sorted(packages.iterdir(), key=lambda path: path.name):
            paths.append(member / "src" / normalized)
    return tuple(
        (path, CandidateProvenance.PROJECT_NAME)
        for path in paths
        if _safe_directory(repository=repository, path=path) is not None
    )


def _ruff_inputs(
    *, repository: Path, project_root: Path, data: Mapping[str, object]
) -> tuple[CandidateInput, ...]:
    ruff: Mapping[str, object] = _table(data=data, keys=("tool", "ruff"))
    inputs: list[CandidateInput] = []
    for value in _strings(value=ruff.get("src")):
        source: Path | None = _safe_directory(repository=repository, path=project_root / value)
        if source is None:
            continue
        if (source / PACKAGE_MARKER_FILE_NAME).is_file():
            inputs.append((source, CandidateProvenance.RUFF_SRC))
        inputs.extend(
            (path, CandidateProvenance.RUFF_SRC) for path in package_children(container=source)
        )
    return tuple(inputs)


def _workspace_members(*, repository: Path, value: str) -> tuple[Path, ...]:
    relative: Path = Path(value)
    if relative.is_absolute() or PARENT_PATH_PART in relative.parts:
        return ()
    if WORKSPACE_WILDCARD not in value:
        member: Path | None = _safe_directory(repository=repository, path=repository / relative)
        return () if member is None else (member,)
    if relative.name != WORKSPACE_WILDCARD or any(
        WORKSPACE_WILDCARD in part for part in relative.parts[:-1]
    ):
        return ()
    parent: Path | None = _safe_directory(repository=repository, path=repository / relative.parent)
    if parent is None:
        return ()
    return tuple(
        path
        for path in sorted(parent.iterdir(), key=lambda item: item.name)
        if path.is_dir() and not path.is_symlink()
    )


def _safe_directory(*, repository: Path, path: Path) -> Path | None:
    resolved: Path = path.resolve()
    try:
        resolved.relative_to(repository)
    except ValueError:
        return None
    if not resolved.is_dir() or path.is_symlink():
        return None
    return path


def _load_toml(*, path: Path, display_path: str) -> Mapping[str, object]:
    if path.is_symlink():
        raise PyprojectParseError(f"Refusing to read symlinked metadata: {display_path}")
    try:
        with path.open("rb") as file:
            data: object = tomllib.load(file)
    except tomllib.TOMLDecodeError as error:
        raise PyprojectParseError(f"Could not parse {display_path}: {error}") from error
    if not isinstance(data, dict):
        raise PyprojectParseError(f"Could not parse {display_path}: expected a TOML table.")
    return cast("Mapping[str, object]", data)


def _table(*, data: Mapping[str, object], keys: tuple[str, ...]) -> Mapping[str, object]:
    current: Mapping[str, object] = data
    for key in keys:
        current = _mapping(value=current.get(key))
    return current


def _mapping(*, value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return {}
    return cast("Mapping[str, object]", value)


def _strings(*, value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)
