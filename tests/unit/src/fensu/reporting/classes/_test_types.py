"""Test case types for semantic CLI styling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CliStyleTestCase:
    """Color setting and exact semantic style output."""

    description: str
    use_color: bool
    expected_rendered: str
