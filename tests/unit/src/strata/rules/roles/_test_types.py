"""Test case types for the roles catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SfrCatalogueTestCase:
    """Expected roles catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int
    expected_sfr204_message: str
    expected_sfr306_symbolic_name: str
    expected_sfr306_slug: str
    expected_sfr306_message: str
    expected_sfr306_remediation: str
    expected_sfr307_message: str
    expected_sfr307_remediation: str
