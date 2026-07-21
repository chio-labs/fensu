"""Test-case types for native core-rule Python boundary coverage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeCoreBoundaryTestCase:
    """One native family diagnostic crossing the Python evaluation boundary."""

    description: str
    rule_code: str
    files: tuple[tuple[str, str], ...]
    expected_path: str
    expected_line: int | None
    roots: tuple[str, ...] = ("src/pkg",)
    tests: tuple[str, ...] = ()
    tooling: tuple[str, ...] = ()
