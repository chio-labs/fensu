"""Published position-fact entry point for discovered files."""

from __future__ import annotations

from strata.discovery.helpers import position
from strata.discovery.models import PositionFacts, ScopedFile


def position_facts(scoped_file: ScopedFile) -> PositionFacts:
    """Return all computed position facts for a scoped file."""

    return PositionFacts(
        relative_parts=scoped_file.relative_parts,
        domain=position.domain(scoped_file),
        subdomain=position.subdomain(scoped_file),
        role=position.role_of(scoped_file),
        is_entry_module=position.is_entry_module(scoped_file),
        is_main_module=position.is_main_module(scoped_file),
    )
