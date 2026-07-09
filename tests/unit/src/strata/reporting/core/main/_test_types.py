"""Test case types for report rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderReportTestCase:
    """Fault rendering inputs and expected text."""

    description: str
    use_color: bool
    expected_text: str
    expected_fault_count: int
