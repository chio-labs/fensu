"""Native snapshot boundary for immutable project-tree facts."""

from fensu.rules.authoring.models import ProjectTree


def project_tree_snapshot(*, tree: ProjectTree) -> dict[str, object]:
    """Return deterministic native replay facts without observing tree queries."""

    from fensu.rules.authoring._helpers.project_tree import project_tree_snapshot as snapshot

    return snapshot(tree=tree)
