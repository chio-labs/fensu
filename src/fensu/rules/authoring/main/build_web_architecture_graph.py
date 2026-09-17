"""Approved construction boundary for resolved web architecture graphs."""

from fensu.rules.authoring._helpers.web_facts import web_architecture_graph
from fensu.rules.authoring.models import ArchitectureGraph, WebWorkspaceFacts


def build_web_architecture_graph(
    *, workspace: WebWorkspaceFacts, ownership_depth: int = 2
) -> ArchitectureGraph:
    """Build a common graph from native-resolved web imports."""

    return web_architecture_graph(workspace=workspace, ownership_depth=ownership_depth)
