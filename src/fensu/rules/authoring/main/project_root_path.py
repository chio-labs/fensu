"""Approved construction entry for the private project-root query sentinel."""

from fensu.rules.authoring._helpers.project_tree import root_path
from fensu.rules.authoring.models import ProjectPath


def project_root_path() -> ProjectPath:
    """Return the private root sentinel used by broad project queries."""

    return root_path()
