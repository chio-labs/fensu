"""Build and serialize immutable discovered project-tree facts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from fensu.config.types import AnalyzerId
from fensu.discovery.constants import INIT_MODULE_FILE_NAME, ROLE_DIR_NAMES
from fensu.discovery.main.position import position_facts
from fensu.discovery.models import (
    DiscoveredTree,
    PositionFacts,
    ProjectSource,
    RepoRoot,
    ScopedFile,
)
from fensu.rules.authoring.constants import (
    CURRENT_PATH_PART,
    PARENT_PATH_PART,
    PROJECT_ROOT,
    WINDOWS_PATH_SEPARATOR,
)
from fensu.rules.authoring.exceptions import ProjectPathError, ProjectPathTypeError
from fensu.rules.authoring.models import (
    File,
    FilePosition,
    ProjectPath,
    ProjectTree,
    PythonFileFacts,
)
from fensu.rules.authoring.types import SourceKind


def build_project_tree(*, tree: DiscoveredTree) -> ProjectTree:
    """Build deterministic public facts from the authoritative discovered tree."""

    project_root: RepoRoot = tree.repo_root if tree.project_root is None else tree.project_root
    scoped_by_path: dict[ProjectPath, ScopedFile] = {
        relative_path(path=file.path, root=project_root): file for file in tree.files
    }
    all_paths: set[ProjectPath] = set(scoped_by_path)
    for file_path in tuple(all_paths):
        for depth in range(1, len(file_path.parts)):
            all_paths.add(ProjectPath(PurePosixPath(*file_path.parts[:depth]).as_posix()))
    ordered_paths: tuple[ProjectPath, ...] = tuple(sorted(all_paths, key=lambda item: item.value))
    project_root_path: ProjectPath = root_path()
    child_lists: dict[ProjectPath, list[ProjectPath]] = {}
    for path in ordered_paths:
        parent: ProjectPath = project_root_path if len(path.parts) == 1 else path.parent
        child_lists.setdefault(parent, []).append(path)
    positions: dict[ProjectPath, FilePosition] = {
        path: file_position(
            path=path,
            scoped_file=scoped_file,
            tree=tree,
            project_root=project_root,
        )
        for path, scoped_file in scoped_by_path.items()
    }
    return ProjectTree(
        _paths=ordered_paths,
        _files=tuple(
            File(path=path) for path in sorted(scoped_by_path, key=lambda item: item.value)
        ),
        _children=MappingProxyType({key: tuple(value) for key, value in child_lists.items()}),
        _positions=MappingProxyType(positions),
        _repository_prefix=(
            project_root.path.relative_to(tree.repo_root.path).as_posix()
            if project_root.path != tree.repo_root.path
            else PROJECT_ROOT
        ),
    )


def project_tree_snapshot(*, tree: ProjectTree) -> dict[str, object]:
    """Return deterministic native replay facts without recording rule observations."""

    return {
        "root_prefix": tree._repository_prefix,
        "paths": [repository_path(tree=tree, path=path.value) for path in tree._paths],
        "files": [repository_path(tree=tree, path=file.path.value) for file in tree._files],
        "positions": {
            repository_path(tree=tree, path=path.value): position_identity(position=position)
            for path, position in sorted(tree._positions.items(), key=lambda item: item[0].value)
        },
    }


def repository_path(*, tree: ProjectTree, path: str) -> str:
    """Return a path relative to the repository rather than the selected project root."""

    return path if tree._repository_prefix == PROJECT_ROOT else f"{tree._repository_prefix}/{path}"


def position_identity(*, position: FilePosition | None) -> str:
    """Serialize one deterministic file-position identity."""

    if position is None:
        return "null"
    return json.dumps(
        {
            "analyzer": position.analyzer.value,
            "domain_parts": list(position.domain_parts),
            "is_entry_module": position.is_entry_module,
            "is_main_module": position.is_main_module,
            "module": position.module,
            "package": position.package,
            "path": position.path.value,
            "role": position.role,
            "role_depth": position.role_depth,
            "scope": position.scope.value,
            "scope_root": position.scope_root.value,
            "source_kind": position.source_kind.value,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def file_position(
    *, path: ProjectPath, scoped_file: ScopedFile, tree: DiscoveredTree, project_root: RepoRoot
) -> FilePosition:
    """Build analyzer-neutral position facts for one discovered file."""

    facts: PositionFacts = position_facts(scoped_file)
    directories: tuple[str, ...] = scoped_file.relative_parts[:-1]
    role_index: int | None = next(
        (index for index, part in enumerate(directories) if part in ROLE_DIR_NAMES), None
    )
    domain_parts: tuple[str, ...] = directories if role_index is None else directories[:role_index]
    module, package = module_identity(scoped_file=scoped_file, tree=tree)
    return FilePosition(
        path=path,
        analyzer=AnalyzerId.PYTHON,
        source_kind=SourceKind.PYTHON_MODULE,
        scope=scoped_file.scope,
        scope_root=relative_path(path=scoped_file.root, root=project_root),
        module=module,
        package=package,
        domain_parts=domain_parts,
        role=facts.role,
        role_depth=(
            None
            if facts.role is None
            else 0
            if role_index is None
            else len(directories) - role_index - 1
        ),
        is_entry_module=facts.is_entry_module,
        is_main_module=facts.is_main_module,
    )


def module_identity(
    *, scoped_file: ScopedFile, tree: DiscoveredTree
) -> tuple[str | None, str | None]:
    """Return the import module and package represented by one discovered file."""

    sources: tuple[ProjectSource, ...] = (
        *tree.layout.runtime_sources,
        *tree.layout.tooling_sources,
    )
    source: ProjectSource | None = next(
        (item for item in sources if item.path == scoped_file.root), None
    )
    if source is None:
        return None, None
    relative: tuple[str, ...] = scoped_file.relative_parts
    module_parts: tuple[str, ...] = (*relative[:-1], scoped_file.path.stem)
    if module_parts[-1] == INIT_MODULE_FILE_NAME.removesuffix(".py"):
        module_parts = module_parts[:-1]
    complete: tuple[str, ...] = (source.package_name, *module_parts)
    module: str = ".".join(complete)
    package_parts: tuple[str, ...] = (
        complete if scoped_file.path.name == INIT_MODULE_FILE_NAME else complete[:-1]
    )
    return module, ".".join(package_parts)


def relative_path(*, path: Path, root: RepoRoot) -> ProjectPath:
    """Convert a discovered filesystem path into a confined public project path."""

    if not isinstance(path, Path):
        raise ProjectPathTypeError("discovered path must be a pathlib.Path")
    return ProjectPath(path.relative_to(root.path).as_posix())


def root_path() -> ProjectPath:
    """Construct the private root sentinel used by broad project queries."""

    value: ProjectPath = object.__new__(ProjectPath)
    object.__setattr__(value, "value", PROJECT_ROOT)
    return value


def python_file_identity(*, value: PythonFileFacts) -> str:
    """Return one deterministic complete Python source fact identity."""

    digest: str = hashlib.sha256(value.source.encode("utf-8")).hexdigest()
    return f"{value.file.path.value}\0{digest}"


def project_path(*, value: ProjectPath | str, allow_root: bool = False) -> ProjectPath:
    """Normalize one supported project-tree query value."""

    if isinstance(value, ProjectPath):
        return value
    if not isinstance(value, str):
        raise ProjectPathTypeError("project tree paths must be ProjectPath or str values")
    if allow_root and value == PROJECT_ROOT:
        return root_path()
    return ProjectPath(value)


def validate_project_path(*, value: object) -> None:
    """Reject invalid public project path values."""

    if not isinstance(value, str) or not value:
        raise ProjectPathError("ProjectPath must be a non-empty string")
    parsed: PurePosixPath = PurePosixPath(value)
    invalid_parts: frozenset[str] = frozenset({CURRENT_PATH_PART, PARENT_PATH_PART})
    if (
        parsed.is_absolute()
        or WINDOWS_PATH_SEPARATOR in value
        or value != parsed.as_posix()
        or any(part in invalid_parts for part in parsed.parts)
        or (parsed.parts and parsed.parts[0].endswith(":"))
    ):
        raise ProjectPathError(
            f"ProjectPath must be a normalized project-relative POSIX path: {value!r}"
        )


def validate_project_glob(*, pattern: object) -> None:
    """Reject invalid or escaping public project glob values."""

    if not isinstance(pattern, str) or not pattern:
        raise ProjectPathError("project glob must be a non-empty string")
    parsed: PurePosixPath = PurePosixPath(pattern)
    invalid_parts: frozenset[str] = frozenset({CURRENT_PATH_PART, PARENT_PATH_PART})
    if (
        parsed.is_absolute()
        or WINDOWS_PATH_SEPARATOR in pattern
        or pattern != parsed.as_posix()
        or any(part in invalid_parts for part in parsed.parts)
        or (parsed.parts and parsed.parts[0].endswith(":"))
    ):
        raise ProjectPathError(
            f"project glob must be a confined project-relative POSIX pattern: {pattern!r}"
        )
