"""Immutable analyzer-neutral architecture graph facts."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from fensu.analysis.models import SourceLocation
from fensu.config.types import AnalyzerId
from fensu.discovery.types import ScopeName
from fensu.rules.authoring.subjects import File, ProjectPath, SourceKind


class ImportResolution(StrEnum):
    """Whether a static import resolves to a discovered project module."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class ModuleVisibility(StrEnum):
    """Structural visibility exposed by a discovered module."""

    PUBLIC = "public"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True, order=True)
class ModuleNode:
    """Stable architecture identity and ownership of one discovered Python module."""

    file: File
    analyzer: AnalyzerId
    source_kind: SourceKind
    module: str
    scope: ScopeName
    scope_root: ProjectPath
    package: str
    domain_parts: tuple[str, ...]
    role: str | None
    visibility: ModuleVisibility


@dataclass(frozen=True, slots=True, order=True)
class AuthoredImport:
    """The import identity written by an author, before project resolution."""

    module_parts: tuple[str, ...]
    imported_parts: tuple[str, ...]
    bound_name: str
    relative_level: int
    from_import: bool


@dataclass(frozen=True, slots=True, order=True)
class ImportEdge:
    """One static authored import and its explicit project-resolution result."""

    source: ModuleNode
    authored: AuthoredImport
    module: str | None
    location: SourceLocation
    status: ImportResolution
    target: ModuleNode | None


@dataclass(frozen=True, slots=True, order=True)
class ImportCycle:
    """One statically proven strongly-connected import component."""

    nodes: tuple[ModuleNode, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureGraph:
    """Resolved static imports from authoritative discovered Python sources.

    Dynamic imports are outside this fact surface: absent runtime-computed imports do not imply
    that no dynamic dependency exists.
    """

    _node_values: tuple[ModuleNode, ...] = field(repr=False)
    _nodes_by_path: Mapping[ProjectPath, ModuleNode] = field(repr=False, compare=False)
    _imports: Mapping[ProjectPath, tuple[ImportEdge, ...]] = field(repr=False, compare=False)
    _dependencies: Mapping[ProjectPath, tuple[ModuleNode, ...]] = field(repr=False, compare=False)
    _dependents: Mapping[ProjectPath, tuple[ModuleNode, ...]] = field(repr=False, compare=False)
    _cycles: tuple[ImportCycle, ...] = field(repr=False)
    _observe: Callable[[str, ProjectPath, str], None] | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def nodes(self) -> tuple[ModuleNode, ...]:
        """Return all graph nodes and observe the broad module inventory."""

        self._record("graph_nodes", _root_path(), _nodes_identity(self._node_values))
        return self._node_values

    def node(self, value: File | ProjectPath) -> ModuleNode | None:
        """Return one discovered module identity without observing the broad inventory."""

        path = value.path if isinstance(value, File) else value
        if not isinstance(path, ProjectPath):
            raise TypeError("graph node queries require a File or ProjectPath")
        answer = self._nodes_by_path.get(path)
        self._record("graph_node", path, _optional_node_identity(answer))
        return answer

    def dependencies(self, value: ModuleNode | File | ProjectPath) -> tuple[ModuleNode, ...]:
        """Return resolved direct targets in stable module order."""

        path = self._path(value)
        answer = self._dependencies.get(path, ())
        self._record("graph_dependencies", path, _nodes_identity(answer))
        return answer

    def dependents(self, value: ModuleNode | File | ProjectPath) -> tuple[ModuleNode, ...]:
        """Return resolved direct importers in stable module order."""

        path = self._path(value)
        answer = self._dependents.get(path, ())
        self._record("graph_dependents", path, _nodes_identity(answer))
        return answer

    def imports(self, value: ModuleNode | File | ProjectPath) -> tuple[ImportEdge, ...]:
        """Return all represented static imports, including explicitly unresolved imports."""

        path = self._path(value)
        answer = self._imports.get(path, ())
        self._record("graph_imports", path, _imports_identity(answer))
        return answer

    def cycles(self) -> tuple[ImportCycle, ...]:
        """Return deterministic statically proven cycles; unresolved imports are excluded."""

        self._record("graph_cycles", _root_path(), _cycles_identity(self._cycles))
        return self._cycles

    def observed(self, observer: Callable[[str, ProjectPath, str], None]) -> ArchitectureGraph:
        """Return a fact view whose query answers are recorded for one rule invocation."""

        return ArchitectureGraph(
            _node_values=self._node_values,
            _nodes_by_path=self._nodes_by_path,
            _imports=self._imports,
            _dependencies=self._dependencies,
            _dependents=self._dependents,
            _cycles=self._cycles,
            _observe=observer,
        )

    def snapshot(self, *, repository_prefix: str) -> dict[str, object]:
        """Return repository-relative replay identities for every supported graph query."""

        def key(path: ProjectPath) -> str:
            return path.value if repository_prefix == "." else f"{repository_prefix}/{path.value}"

        return {
            "root_prefix": repository_prefix,
            "nodes": _nodes_identity(self._node_values),
            "node": {
                key(node.file.path): _optional_node_identity(node) for node in self._node_values
            },
            "dependencies": {
                key(path): _nodes_identity(value) for path, value in self._dependencies.items()
            },
            "dependents": {
                key(path): _nodes_identity(value) for path, value in self._dependents.items()
            },
            "imports": {
                key(path): _imports_identity(value) for path, value in self._imports.items()
            },
            "cycles": _cycles_identity(self._cycles),
        }

    def _path(self, value: ModuleNode | File | ProjectPath) -> ProjectPath:
        if isinstance(value, ModuleNode):
            path = value.file.path
        elif isinstance(value, File):
            path = value.path
        elif isinstance(value, ProjectPath):
            path = value
        else:
            raise TypeError("graph queries require a ModuleNode, File, or ProjectPath")
        if path not in self._nodes_by_path:
            raise ValueError(f"graph path is not a discovered Python module: {path}")
        return path

    def _record(self, kind: str, path: ProjectPath, answer: str) -> None:
        if self._observe is not None:
            self._observe(kind, path, answer)


def architecture_graph(
    *,
    nodes: tuple[ModuleNode, ...],
    imports: Mapping[ProjectPath, tuple[ImportEdge, ...]],
) -> ArchitectureGraph:
    """Assemble deterministic reverse edges and proven strongly-connected components."""

    ordered_nodes = tuple(sorted(nodes, key=lambda node: (node.module, node.file.path.value)))
    dependencies: dict[ProjectPath, tuple[ModuleNode, ...]] = {}
    reverse: dict[ProjectPath, set[ModuleNode]] = {node.file.path: set() for node in ordered_nodes}
    normalized_imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {}
    for node in ordered_nodes:
        edges = tuple(sorted(set(imports.get(node.file.path, ())), key=_edge_key))
        normalized_imports[node.file.path] = edges
        targets = tuple(
            sorted(
                {edge.target for edge in edges if edge.target is not None},
                key=lambda target: (target.module, target.file.path.value),
            )
        )
        dependencies[node.file.path] = targets
        for target in targets:
            reverse[target.file.path].add(node)
    dependents = {
        path: tuple(sorted(values, key=lambda node: (node.module, node.file.path.value)))
        for path, values in reverse.items()
    }
    cycles = _strong_components(nodes=ordered_nodes, dependencies=dependencies)
    return ArchitectureGraph(
        _node_values=ordered_nodes,
        _nodes_by_path=MappingProxyType({node.file.path: node for node in ordered_nodes}),
        _imports=MappingProxyType(normalized_imports),
        _dependencies=MappingProxyType(dependencies),
        _dependents=MappingProxyType(dependents),
        _cycles=cycles,
    )


def _strong_components(
    *, nodes: tuple[ModuleNode, ...], dependencies: Mapping[ProjectPath, tuple[ModuleNode, ...]]
) -> tuple[ImportCycle, ...]:
    by_path = {node.file.path: node for node in nodes}
    adjacency = {
        node.file.path: tuple(target.file.path for target in dependencies.get(node.file.path, ()))
        for node in nodes
    }
    reverse: dict[ProjectPath, list[ProjectPath]] = {path: [] for path in by_path}
    for source, targets in adjacency.items():
        for target in targets:
            reverse[target].append(source)
    for values in reverse.values():
        values.sort(key=lambda path: (by_path[path].module, path.value))

    visited: set[ProjectPath] = set()
    finish_order: list[ProjectPath] = []
    for node in nodes:
        start = node.file.path
        if start in visited:
            continue
        visited.add(start)
        stack: list[tuple[ProjectPath, int]] = [(start, 0)]
        while stack:
            path, next_index = stack[-1]
            targets = adjacency[path]
            if next_index >= len(targets):
                stack.pop()
                finish_order.append(path)
                continue
            target = targets[next_index]
            stack[-1] = (path, next_index + 1)
            if target not in visited:
                visited.add(target)
                stack.append((target, 0))

    assigned: set[ProjectPath] = set()
    components: list[ImportCycle] = []
    for start in reversed(finish_order):
        if start in assigned:
            continue
        assigned.add(start)
        pending = [start]
        paths: list[ProjectPath] = []
        while pending:
            path = pending.pop()
            paths.append(path)
            for source in reversed(reverse[path]):
                if source not in assigned:
                    assigned.add(source)
                    pending.append(source)
        ordered = tuple(
            sorted(
                (by_path[path] for path in paths),
                key=lambda item: (item.module, item.file.path.value),
            )
        )
        self_edge = len(ordered) == 1 and start in adjacency[start]
        if len(ordered) > 1 or self_edge:
            components.append(ImportCycle(nodes=ordered))
    return tuple(sorted(components, key=lambda cycle: tuple(node.module for node in cycle.nodes)))


def _edge_key(edge: ImportEdge) -> tuple[object, ...]:
    return (
        edge.location.path.as_posix(),
        edge.location.line,
        edge.location.column,
        edge.authored,
        edge.module or "",
        edge.status,
        "" if edge.target is None else edge.target.module,
    )


def _node_value(node: ModuleNode) -> dict[str, object]:
    return {
        "analyzer": node.analyzer.value,
        "domain_parts": list(node.domain_parts),
        "module": node.module,
        "package": node.package,
        "path": node.file.path.value,
        "role": node.role,
        "scope": node.scope.value,
        "scope_root": node.scope_root.value,
        "source_kind": node.source_kind.value,
        "visibility": node.visibility.value,
    }


def _nodes_identity(nodes: tuple[ModuleNode, ...]) -> str:
    return json.dumps([_node_value(node) for node in nodes], sort_keys=True, separators=(",", ":"))


def _optional_node_identity(node: ModuleNode | None) -> str:
    return json.dumps(
        None if node is None else _node_value(node), sort_keys=True, separators=(",", ":")
    )


def _imports_identity(edges: tuple[ImportEdge, ...]) -> str:
    return json.dumps(
        [
            {
                "authored": {
                    "bound_name": edge.authored.bound_name,
                    "from_import": edge.authored.from_import,
                    "imported_parts": list(edge.authored.imported_parts),
                    "module_parts": list(edge.authored.module_parts),
                    "relative_level": edge.authored.relative_level,
                },
                "location": {
                    "column": edge.location.column,
                    "line": edge.location.line,
                    "path": edge.source.file.path.value,
                },
                "module": edge.module,
                "source": _node_value(edge.source),
                "status": edge.status.value,
                "target": None if edge.target is None else _node_value(edge.target),
            }
            for edge in edges
        ],
        sort_keys=True,
        separators=(",", ":"),
    )


def _cycles_identity(cycles: tuple[ImportCycle, ...]) -> str:
    return json.dumps(
        [[_node_value(node) for node in cycle.nodes] for cycle in cycles],
        sort_keys=True,
        separators=(",", ":"),
    )


def _root_path() -> ProjectPath:
    value = object.__new__(ProjectPath)
    object.__setattr__(value, "value", ".")
    return value
