"""Test-case types for native discovery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryParityTestCase:
    """One fixture tree with a minimum expected native discovery count."""

    description: str
    files: tuple[str, ...]
    directory_symlinks: tuple[tuple[str, str], ...]
    file_symlinks: tuple[tuple[str, str], ...]
    expected_minimum_files: int
