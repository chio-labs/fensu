"""Internal entry point for constructing evaluation architecture graph facts."""

from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.classes.architecture_graph_builder import ArchitectureGraphBuilder
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.models import ArchitectureGraph


def build_architecture_graph(
    *, tree: DiscoveredTree, analysis: EvaluationProjectAnalysis
) -> ArchitectureGraph:
    """Build graph facts from authoritative discovery and parsed import facts."""

    return ArchitectureGraphBuilder(tree=tree, analysis=analysis).build()
