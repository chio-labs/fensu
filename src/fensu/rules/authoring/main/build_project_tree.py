"""Public construction boundary for immutable project-tree facts."""

from fensu.discovery.models import DiscoveredTree
from fensu.rules.authoring.models import ProjectTree


def build_project_tree(*, tree: DiscoveredTree) -> ProjectTree:
    """Build deterministic public facts from the authoritative discovered tree."""

    from fensu.rules.authoring._helpers.project_tree import build_project_tree as build

    return build(tree=tree)
