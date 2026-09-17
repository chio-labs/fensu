"""Approved construction boundary for web project-tree facts."""

from fensu.rules.authoring._helpers.web_facts import web_project_tree
from fensu.rules.authoring.models import ProjectTree, WebWorkspaceFacts


def build_web_project_tree(
    *, subjects: object, workspace: WebWorkspaceFacts, ownership_depth: int = 2
) -> ProjectTree:
    """Build the deterministic common tree for selected file subjects."""

    return web_project_tree(
        subjects=subjects,
        workspace=workspace,
        ownership_depth=ownership_depth,
    )
