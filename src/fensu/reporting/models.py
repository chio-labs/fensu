"""Reporting output models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderedReport:
    """Rendered report text plus summary facts."""

    text: str
    fault_count: int
    warning_count: int = 0
    applied_exception_count: int = 0
