"""Test case types for the roles catalogue."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.rules.authoring.types import ExecutionOwner


@dataclass(frozen=True)
class FfrCatalogueTestCase:
    """Expected roles catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int
    expected_sfr204_message: str
    expected_sfr301_owner: ExecutionOwner
    expected_sfr302_owner: ExecutionOwner
    expected_sfr303_slug: str
    expected_sfr303_message: str
    expected_sfr303_remediation: str
    expected_sfr306_symbolic_name: str
    expected_sfr306_slug: str
    expected_sfr306_message: str
    expected_sfr306_remediation: str
    expected_sfr306_owner: ExecutionOwner
    expected_sfr307_message: str
    expected_sfr307_remediation: str
    expected_sfr308_slug: str
    expected_sfr308_message: str
    expected_sfr308_remediation: str
    expected_sfr308_owner: ExecutionOwner
    expected_sfr309_slug: str
    expected_sfr309_message: str
    expected_sfr309_remediation: str
    expected_sfr309_owner: ExecutionOwner
    expected_sfr706_slug: str
    expected_sfr706_message: str
    expected_sfr706_remediation: str
