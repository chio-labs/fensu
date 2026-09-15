"""Approved selection entry for serialized Rust workspace facts."""

from __future__ import annotations

from collections.abc import Mapping

from fensu.rules.authoring._helpers.rust_facts import selected_rust_workspace
from fensu.rules.authoring.models import ProjectPath, RustFileFacts, RustWorkspaceFacts


def select_rust_workspace_facts(
    *, workspace: RustWorkspaceFacts, files: Mapping[ProjectPath, RustFileFacts]
) -> RustWorkspaceFacts:
    """Restrict workspace file facts to configured authoritative subjects."""

    return selected_rust_workspace(workspace=workspace, files=files)
