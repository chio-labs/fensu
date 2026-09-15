"""Focused tests for architecture graph assembly."""

import sys

import pytest

from fensu import ArchitectureGraph, ImportEdge, ModuleNode, ProjectPath
from fensu.rules.authoring._helpers.architecture_graph import architecture_graph
from tests.unit.src.fensu.rules.authoring._test_types import IterativeGraphCycleTestCase
from tests.unit.src.fensu.rules.authoring.helpers import graph_edge, graph_node


@pytest.mark.parametrize(
    "test_case",
    [
        IterativeGraphCycleTestCase(
            description="cycle longer than the interpreter recursion limit",
            recursion_limit_offset=10,
            expected_cycle_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_import_chain_longer_than_recursion_limit_when_computing_cycles_then_stays_iterative(
    test_case: IterativeGraphCycleTestCase,
) -> None:
    count: int = sys.getrecursionlimit() + test_case.recursion_limit_offset
    nodes: tuple[ModuleNode, ...] = tuple(graph_node(index) for index in range(count))
    imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {
        node.file.path: (graph_edge(source=node, target=nodes[(index + 1) % count]),)
        for index, node in enumerate(nodes)
    }

    graph: ArchitectureGraph = architecture_graph(nodes=nodes, imports=imports)

    assert len(graph.cycles()) == test_case.expected_cycle_count
    assert len(graph.cycles()[0].nodes) == count


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-vv"])
