"""Approved construction entry for serialized Python repository target facts."""

from fensu.rules.authoring._helpers.python_repository_facts import (
    build_python_repository_facts as build,
)
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    ProjectTree,
    PythonWorkspaceFacts,
)


def build_python_repository_facts(
    *, payload: object, subjects: object
) -> tuple[PythonWorkspaceFacts, ProjectTree, ArchitectureGraph]:
    """Decode one native Python target snapshot into immutable public facts."""

    return build(payload=payload, subjects=subjects)
