"""Construction boundary for immutable architecture graph facts."""

from collections.abc import Mapping

from fensu.rules.authoring.models import ArchitectureGraph, ImportEdge, ModuleNode, ProjectPath


def architecture_graph(
    *, nodes: tuple[ModuleNode, ...], imports: Mapping[ProjectPath, tuple[ImportEdge, ...]]
) -> ArchitectureGraph:
    """Assemble deterministic reverse edges and strongly-connected components."""

    from fensu.rules.authoring._helpers.architecture_graph import architecture_graph as assemble

    return assemble(nodes=nodes, imports=imports)
