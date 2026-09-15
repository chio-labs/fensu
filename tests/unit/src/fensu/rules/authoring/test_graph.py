"""Focused tests for architecture graph assembly."""

import sys
from pathlib import Path

from fensu.analysis.models import SourceLocation
from fensu.config.types import AnalyzerId
from fensu.discovery.types import ScopeName
from fensu.rules.authoring.graph import (
    AuthoredImport,
    ImportEdge,
    ImportResolution,
    ModuleNode,
    ModuleVisibility,
    architecture_graph,
)
from fensu.rules.authoring.subjects import File, ProjectPath, SourceKind


def test_given_import_chain_longer_than_recursion_limit_when_computing_cycles_then_stays_iterative() -> (
    None
):
    count = sys.getrecursionlimit() + 10
    nodes = tuple(_node(index) for index in range(count))
    imports = {
        node.file.path: (_edge(source=node, target=nodes[(index + 1) % count]),)
        for index, node in enumerate(nodes)
    }

    graph = architecture_graph(nodes=nodes, imports=imports)

    assert len(graph.cycles()) == 1
    assert len(graph.cycles()[0].nodes) == count


def _node(index: int) -> ModuleNode:
    return ModuleNode(
        file=File(ProjectPath(f"src/example/module_{index:04}.py")),
        analyzer=AnalyzerId.PYTHON,
        source_kind=SourceKind.PYTHON_MODULE,
        module=f"example.module_{index:04}",
        scope=ScopeName.ROOT,
        scope_root=ProjectPath("src/example"),
        package="example",
        domain_parts=(),
        role=None,
        visibility=ModuleVisibility.INTERNAL,
    )


def _edge(*, source: ModuleNode, target: ModuleNode) -> ImportEdge:
    return ImportEdge(
        source=source,
        authored=AuthoredImport(
            module_parts=(),
            imported_parts=tuple(target.module.split(".")),
            bound_name="example",
            relative_level=0,
            from_import=False,
        ),
        module=target.module,
        location=SourceLocation(path=Path(source.file.path.value), line=1, column=0),
        status=ImportResolution.RESOLVED,
        target=target,
    )


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-vv"])
