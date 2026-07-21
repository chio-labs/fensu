"""Test-case types for the installed custom-rule authoring index."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthoringIndexTestCase:
    """Expected discoverable sections in the installed authoring index."""

    description: str
    section_names: tuple[str, ...]
    expected_counts: tuple[int, ...]
