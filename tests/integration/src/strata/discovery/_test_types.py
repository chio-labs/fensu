"""Test-case types for discovery backend parity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryParityTestCase:
    """One fixture tree whose discovery must match across fact backends."""

    description: str
    files: tuple[str, ...]
    directory_symlinks: tuple[tuple[str, str], ...]
    file_symlinks: tuple[tuple[str, str], ...]
    expected_minimum_files: int
