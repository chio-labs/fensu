"""Approved construction entry for native serialized Rust facts."""

from __future__ import annotations

from fensu.rules.authoring._helpers.rust_facts import rust_workspace_facts
from fensu.rules.authoring.models import RustWorkspaceFacts


def build_rust_workspace_facts(*, payload: object) -> RustWorkspaceFacts:
    """Build immutable public facts from one versioned native payload."""

    return rust_workspace_facts(payload=payload)
