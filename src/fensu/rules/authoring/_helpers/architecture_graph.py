"""Assemble and serialize immutable architecture graph facts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from types import MappingProxyType

from fensu.rules.authoring.constants import PROJECT_ROOT
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    ImportCycle,
    ImportEdge,
    ModuleNode,
    ProjectPath,
)


def architecture_graph(
    *, nodes: tuple[ModuleNode, ...], imports: Mapping[ProjectPath, tuple[ImportEdge, ...]]
) -> ArchitectureGraph:
    """Assemble deterministic reverse edges and strongly-connected components."""

    ordered_nodes: tuple[ModuleNode, ...] = tuple(
        sorted(nodes, key=lambda node: (node.module, node.file.path.value))
    )
    dependencies: dict[ProjectPath, tuple[ModuleNode, ...]] = {}
    reverse: dict[ProjectPath, set[ModuleNode]] = {node.file.path: set() for node in ordered_nodes}
    normalized_imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {}
    for node in ordered_nodes:
        edges: tuple[ImportEdge, ...] = tuple(
            sorted(set(imports.get(node.file.path, ())), key=edge_key)
        )
        normalized_imports[node.file.path] = edges
        targets: tuple[ModuleNode, ...] = tuple(
            sorted(
                {edge.target for edge in edges if edge.target is not None},
                key=lambda target: (target.module, target.file.path.value),
            )
        )
        dependencies[node.file.path] = targets
        for target in targets:
            reverse[target.file.path].add(node)
    dependents: dict[ProjectPath, tuple[ModuleNode, ...]] = {
        path: tuple(sorted(values, key=lambda node: (node.module, node.file.path.value)))
        for path, values in reverse.items()
    }
    cycles: tuple[ImportCycle, ...] = strong_components(
        nodes=ordered_nodes, dependencies=dependencies
    )
    return ArchitectureGraph(
        _node_values=ordered_nodes,
        _nodes_by_path=MappingProxyType({node.file.path: node for node in ordered_nodes}),
        _imports=MappingProxyType(normalized_imports),
        _dependencies=MappingProxyType(dependencies),
        _dependents=MappingProxyType(dependents),
        _cycles=cycles,
    )


def strong_components(
    *, nodes: tuple[ModuleNode, ...], dependencies: Mapping[ProjectPath, tuple[ModuleNode, ...]]
) -> tuple[ImportCycle, ...]:
    """Return deterministic cyclic strongly-connected graph components."""

    by_path: dict[ProjectPath, ModuleNode] = {node.file.path: node for node in nodes}
    adjacency: dict[ProjectPath, tuple[ProjectPath, ...]] = {}
    for node in nodes:
        adjacency[node.file.path] = tuple(
            target.file.path for target in dependencies.get(node.file.path, ())
        )
    reverse: dict[ProjectPath, list[ProjectPath]] = {path: [] for path in by_path}
    for source, targets in adjacency.items():
        for target in targets:
            reverse[target].append(source)
    for values in reverse.values():
        values.sort(key=lambda path: (by_path[path].module, path.value))
    finish_order: list[ProjectPath] = graph_finish_order(nodes=nodes, adjacency=adjacency)
    components: list[ImportCycle] = []
    assigned: set[ProjectPath] = set()
    for start in reversed(finish_order):
        if start in assigned:
            continue
        assigned.add(start)
        pending: list[ProjectPath] = [start]
        paths: list[ProjectPath] = []
        while pending:
            path: ProjectPath = pending.pop()
            paths.append(path)
            for source in reversed(reverse[path]):
                if source not in assigned:
                    assigned.add(source)
                    pending.append(source)
        ordered: tuple[ModuleNode, ...] = tuple(
            sorted(
                (by_path[path] for path in paths),
                key=lambda item: (item.module, item.file.path.value),
            )
        )
        self_edge: bool = len(ordered) == 1 and start in adjacency[start]
        if len(ordered) > 1 or self_edge:
            components.append(ImportCycle(nodes=ordered))
    return tuple(sorted(components, key=lambda cycle: tuple(node.module for node in cycle.nodes)))


def graph_finish_order(
    *, nodes: tuple[ModuleNode, ...], adjacency: Mapping[ProjectPath, tuple[ProjectPath, ...]]
) -> list[ProjectPath]:
    """Return iterative depth-first completion order for every graph node."""

    visited: set[ProjectPath] = set()
    finish_order: list[ProjectPath] = []
    for node in nodes:
        start: ProjectPath = node.file.path
        if start in visited:
            continue
        visited.add(start)
        stack: list[tuple[ProjectPath, int]] = [(start, 0)]
        while stack:
            path, next_index = stack[-1]
            targets: tuple[ProjectPath, ...] = adjacency[path]
            if next_index >= len(targets):
                stack.pop()
                finish_order.append(path)
                continue
            target: ProjectPath = targets[next_index]
            stack[-1] = (path, next_index + 1)
            if target not in visited:
                visited.add(target)
                stack.append((target, 0))
    return finish_order


def edge_key(edge: ImportEdge) -> tuple[object, ...]:
    """Return the stable ordering identity for one import edge."""

    return (
        edge.location.path.as_posix(),
        edge.location.line,
        edge.location.column,
        edge.authored,
        edge.module or "",
        edge.status,
        "" if edge.target is None else edge.target.module,
    )


def node_value(node: ModuleNode) -> dict[str, object]:
    """Return the JSON-compatible stable identity for one module node."""

    return {
        "analyzer": node.analyzer.value,
        "domain_parts": list(node.domain_parts),
        "module": node.module,
        "ownership_root": None if node.ownership_root is None else node.ownership_root.value,
        "package": node.package,
        "path": node.file.path.value,
        "role": node.role,
        "scope": node.scope.value,
        "scope_root": node.scope_root.value,
        "source_kind": node.source_kind.value,
        "visibility": node.visibility.value,
    }


def nodes_identity(nodes: tuple[ModuleNode, ...]) -> str:
    """Serialize an ordered module-node collection."""

    return json.dumps([node_value(node) for node in nodes], sort_keys=True, separators=(",", ":"))


def optional_node_identity(node: ModuleNode | None) -> str:
    """Serialize an optional module-node query result."""

    return json.dumps(
        None if node is None else node_value(node), sort_keys=True, separators=(",", ":")
    )


def imports_identity(edges: tuple[ImportEdge, ...]) -> str:
    """Serialize an ordered import-edge collection."""

    values: list[dict[str, object]] = []
    for edge in edges:
        values.append(
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
                "source": node_value(edge.source),
                "status": edge.status.value,
                "target": None if edge.target is None else node_value(edge.target),
            }
        )
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def cycles_identity(cycles: tuple[ImportCycle, ...]) -> str:
    """Serialize deterministic cycle node identities."""

    values: list[list[dict[str, object]]] = []
    for cycle in cycles:
        values.append([node_value(node) for node in cycle.nodes])
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def repository_graph_path(*, path: ProjectPath, repository_prefix: str) -> str:
    """Return a graph path relative to the repository root."""

    return path.value if repository_prefix == PROJECT_ROOT else f"{repository_prefix}/{path.value}"


def root_path() -> ProjectPath:
    """Construct the private root sentinel used by broad graph queries."""

    value: ProjectPath = object.__new__(ProjectPath)
    object.__setattr__(value, "value", PROJECT_ROOT)
    return value
