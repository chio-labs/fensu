"""Immutable analyzer-neutral subjects and discovered-tree facts."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path as FileSystemPath
from pathlib import PurePosixPath
from types import MappingProxyType

from fensu.config.types import AnalyzerId
from fensu.discovery.constants import INIT_MODULE_FILE_NAME, ROLE_DIR_NAMES
from fensu.discovery.main.position import position_facts
from fensu.discovery.models import DiscoveredTree, ProjectSource, RepoRoot, ScopedFile
from fensu.discovery.types import ScopeName

_PROJECT_ROOT = "."
_WINDOWS_SEPARATOR = "\\"


class SourceKind(StrEnum):
    """Analyzer-neutral source representation identity."""

    PYTHON_MODULE = "python_module"


@dataclass(frozen=True, slots=True, order=True)
class ProjectPath:
    """A normalized POSIX path confined to the analyzed project."""

    value: str

    def __post_init__(self) -> None:
        """Reject absolute, platform-specific, and escaping path spellings."""

        if not isinstance(self.value, str) or not self.value:
            raise ValueError("ProjectPath must be a non-empty string")
        parsed = PurePosixPath(self.value)
        if (
            parsed.is_absolute()
            or _WINDOWS_SEPARATOR in self.value
            or self.value != parsed.as_posix()
            or any(part in {".", ".."} for part in parsed.parts)
            or (parsed.parts and parsed.parts[0].endswith(":"))
        ):
            raise ValueError(
                f"ProjectPath must be a normalized project-relative POSIX path: {self.value!r}"
            )

    @property
    def parts(self) -> tuple[str, ...]:
        """Return normalized path components."""

        return PurePosixPath(self.value).parts

    @property
    def name(self) -> str:
        """Return the final path component."""

        return PurePosixPath(self.value).name

    @property
    def parent(self) -> ProjectPath:
        """Return the containing project path."""

        return ProjectPath(PurePosixPath(self.value).parent.as_posix())

    def as_posix(self) -> str:
        """Return the portable project-relative spelling."""

        return self.value

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class File:
    """Stable identity of one discovered source file."""

    path: ProjectPath


@dataclass(frozen=True, slots=True)
class Project:
    """Stable identity of the analyzed project."""


@dataclass(frozen=True, slots=True)
class FilePosition:
    """Stable analyzer-neutral architecture position of one discovered file."""

    path: ProjectPath
    analyzer: AnalyzerId
    source_kind: SourceKind
    scope: ScopeName
    scope_root: ProjectPath
    module: str | None
    package: str | None
    domain_parts: tuple[str, ...]
    role: str | None
    role_depth: int | None
    is_entry_module: bool
    is_main_module: bool


@dataclass(frozen=True, slots=True)
class ProjectTree:
    """Immutable facts derived only from the authoritative discovered tree."""

    _paths: tuple[ProjectPath, ...]
    _files: tuple[File, ...]
    _children: Mapping[ProjectPath, tuple[ProjectPath, ...]] = field(repr=False, compare=False)
    _positions: Mapping[ProjectPath, FilePosition] = field(repr=False, compare=False)
    _repository_prefix: str = field(default=_PROJECT_ROOT, repr=False, compare=False)
    _observe: (
        Callable[[str, ProjectPath, str | tuple[ProjectPath, ...], str | None], None] | None
    ) = field(default=None, repr=False, compare=False)

    @property
    def paths(self) -> tuple[ProjectPath, ...]:
        """Return all discovered paths and observe the broad inventory query."""

        self._record("tree_paths", _root_path(), self._paths)
        return self._paths

    @property
    def files(self) -> tuple[File, ...]:
        """Return all discovered files and observe the broad file inventory query."""

        self._record("tree_files", _root_path(), tuple(file.path for file in self._files))
        return self._files

    def children(self, path: ProjectPath | str = _PROJECT_ROOT) -> tuple[ProjectPath, ...]:
        """Return immediate discovered children in lexical POSIX order."""

        query = _path(path, allow_root=True)
        answer = self._children.get(query, ())
        self._record("tree_children", query, answer)
        return answer

    def descendants(self, path: ProjectPath | str = _PROJECT_ROOT) -> tuple[ProjectPath, ...]:
        """Return every discovered descendant in lexical POSIX order."""

        parent = _path(path, allow_root=True)
        prefix = () if parent.value == _PROJECT_ROOT else parent.parts
        answer = tuple(
            candidate
            for candidate in self._paths
            if len(candidate.parts) > len(prefix) and candidate.parts[: len(prefix)] == prefix
        )
        self._record("tree_descendants", parent, answer)
        return answer

    def glob(self, pattern: str) -> tuple[ProjectPath, ...]:
        """Return paths matching one confined project-relative POSIX glob."""

        _validate_glob(pattern)
        answer = tuple(path for path in self._paths if PurePosixPath(path.value).match(pattern))
        self._record("tree_glob", _root_path(), answer, pattern)
        return answer

    def files_under(self, path: ProjectPath | str = _PROJECT_ROOT) -> tuple[File, ...]:
        """Return discovered files at or below a project path."""

        parent = _path(path, allow_root=True)
        prefix = () if parent.value == _PROJECT_ROOT else parent.parts
        answer = tuple(
            file
            for file in self._files
            if file.path == parent
            or (len(file.path.parts) > len(prefix) and file.path.parts[: len(prefix)] == prefix)
        )
        self._record("tree_files_under", parent, tuple(file.path for file in answer))
        return answer

    def position(self, path: ProjectPath | str) -> FilePosition | None:
        """Return complete architecture position facts for a discovered file."""

        query = _path(path)
        answer = self._positions.get(query)
        self._record("tree_position", query, _position_identity(answer))
        return answer

    def observed(
        self,
        observer: Callable[[str, ProjectPath, str | tuple[ProjectPath, ...], str | None], None],
    ) -> ProjectTree:
        """Return an immutable view whose accesses are bound to one requester."""

        return ProjectTree(
            _paths=self._paths,
            _files=self._files,
            _children=self._children,
            _positions=self._positions,
            _repository_prefix=self._repository_prefix,
            _observe=observer,
        )

    def _record(
        self,
        kind: str,
        query: ProjectPath,
        answer: str | tuple[ProjectPath, ...],
        pattern: str | None = None,
    ) -> None:
        if self._observe is not None:
            self._observe(kind, query, answer, pattern)


def build_project_tree(*, tree: DiscoveredTree) -> ProjectTree:
    """Build deterministic public facts from the authoritative discovered tree."""

    project_root: RepoRoot = tree.repo_root if tree.project_root is None else tree.project_root
    scoped_by_path: dict[ProjectPath, ScopedFile] = {
        _relative_path(path=file.path, root=project_root): file for file in tree.files
    }
    all_paths: set[ProjectPath] = set(scoped_by_path)
    for file_path in tuple(all_paths):
        for depth in range(1, len(file_path.parts)):
            all_paths.add(ProjectPath(PurePosixPath(*file_path.parts[:depth]).as_posix()))
    ordered_paths = tuple(sorted(all_paths, key=lambda item: item.value))
    root_path = _root_path()
    child_lists: dict[ProjectPath, list[ProjectPath]] = {}
    for path in ordered_paths:
        parent = root_path if len(path.parts) == 1 else path.parent
        child_lists.setdefault(parent, []).append(path)
    positions = {
        path: _file_position(
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
            else _PROJECT_ROOT
        ),
    )


def project_tree_snapshot(*, tree: ProjectTree) -> dict[str, object]:
    """Return deterministic native replay facts without recording rule observations."""

    return {
        "root_prefix": tree._repository_prefix,
        "paths": [_repository_path(tree, path.value) for path in tree._paths],
        "files": [_repository_path(tree, file.path.value) for file in tree._files],
        "positions": {
            _repository_path(tree, path.value): _position_identity(position)
            for path, position in sorted(tree._positions.items(), key=lambda item: item[0].value)
        },
    }


def _repository_path(tree: ProjectTree, path: str) -> str:
    return path if tree._repository_prefix == _PROJECT_ROOT else f"{tree._repository_prefix}/{path}"


def _position_identity(position: FilePosition | None) -> str:
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


def _file_position(
    *,
    path: ProjectPath,
    scoped_file: ScopedFile,
    tree: DiscoveredTree,
    project_root: RepoRoot,
) -> FilePosition:
    facts = position_facts(scoped_file)
    directories = scoped_file.relative_parts[:-1]
    role_index = next(
        (index for index, part in enumerate(directories) if part in ROLE_DIR_NAMES), None
    )
    domain_parts = directories if role_index is None else directories[:role_index]
    module, package = _module_identity(scoped_file=scoped_file, tree=tree)
    return FilePosition(
        path=path,
        analyzer=AnalyzerId.PYTHON,
        source_kind=SourceKind.PYTHON_MODULE,
        scope=scoped_file.scope,
        scope_root=_relative_path(path=scoped_file.root, root=project_root),
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


def _module_identity(
    *, scoped_file: ScopedFile, tree: DiscoveredTree
) -> tuple[str | None, str | None]:
    sources: tuple[ProjectSource, ...] = (
        *tree.layout.runtime_sources,
        *tree.layout.tooling_sources,
    )
    source = next((item for item in sources if item.path == scoped_file.root), None)
    if source is None:
        return None, None
    relative = scoped_file.relative_parts
    module_parts = (*relative[:-1], scoped_file.path.stem)
    if module_parts[-1] == INIT_MODULE_FILE_NAME.removesuffix(".py"):
        module_parts = module_parts[:-1]
    complete = (source.package_name, *module_parts)
    module = ".".join(complete)
    package_parts = complete if scoped_file.path.name == INIT_MODULE_FILE_NAME else complete[:-1]
    return module, ".".join(package_parts)


def _relative_path(*, path: FileSystemPath, root: RepoRoot) -> ProjectPath:
    if not isinstance(path, FileSystemPath):
        raise TypeError("discovered path must be a pathlib.Path")
    return ProjectPath(path.relative_to(root.path).as_posix())


def _root_path() -> ProjectPath:
    value = object.__new__(ProjectPath)
    object.__setattr__(value, "value", _PROJECT_ROOT)
    return value


def _path(value: ProjectPath | str, *, allow_root: bool = False) -> ProjectPath:
    if isinstance(value, ProjectPath):
        return value
    if not isinstance(value, str):
        raise TypeError("project tree paths must be ProjectPath or str values")
    if allow_root and value == _PROJECT_ROOT:
        return _root_path()
    return ProjectPath(value)


def _validate_glob(pattern: str) -> None:
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("project glob must be a non-empty string")
    parsed = PurePosixPath(pattern)
    if (
        parsed.is_absolute()
        or _WINDOWS_SEPARATOR in pattern
        or pattern != parsed.as_posix()
        or any(part in {".", ".."} for part in parsed.parts)
        or (parsed.parts and parsed.parts[0].endswith(":"))
    ):
        raise ValueError(
            f"project glob must be a confined project-relative POSIX pattern: {pattern!r}"
        )
