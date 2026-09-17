"""Approved construction boundary for resolved web architecture graphs."""

from fensu.rules.authoring._helpers.web_facts import web_architecture_graph
from fensu.rules.authoring.models import ArchitectureGraph, WebWorkspaceFacts


def build_web_architecture_graph(
    *,
    workspace: WebWorkspaceFacts,
    ownership_roots: tuple[str, ...] = (),
    subjects: object | None = None,
) -> ArchitectureGraph:
    """Build a common graph from native-resolved web imports."""

    return web_architecture_graph(
        workspace=workspace,
        ownership_roots=ownership_roots,
        subjects=subjects,
    )
