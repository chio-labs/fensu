"""Approved project-tree construction entry for native Rust subjects."""

from __future__ import annotations

from collections.abc import Mapping

from fensu.rules.authoring._helpers.rust_facts import rust_project_tree
from fensu.rules.authoring.models import ProjectPath, ProjectTree, RustFileFacts, RustWorkspaceFacts


def build_rust_project_tree(
    *, subjects: object, workspace: RustWorkspaceFacts, ownership_depth: int = 2
) -> tuple[ProjectTree, Mapping[ProjectPath, RustFileFacts]]:
    """Build the common project tree and selected-file fact index."""

    return rust_project_tree(
        subjects=subjects,
        workspace=workspace,
        ownership_depth=ownership_depth,
    )
