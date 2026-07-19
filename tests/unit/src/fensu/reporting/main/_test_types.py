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


@dataclass(frozen=True)
class RemediationRenderTestCase:
    """Expected message/help separation for one rendered fault."""

    description: str
    use_color: bool
    expected_text_fragments: tuple[str, ...]


@dataclass(frozen=True)
class ExceptionRenderTestCase:
    """Applied exception count and expected report summary."""

    description: str
    applied_exception_count: int
    expected_text: str


@dataclass(frozen=True)
class EvaluationRenderTestCase:
    """Evaluation metadata and expected report footer hierarchy."""

    description: str
    use_color: bool
    evaluation_summary: str
    applied_exception_count: int
    expected_text: str


@dataclass(frozen=True)
class WarningRenderTestCase:
    """Warning rendering mode and expected labeled summary behavior."""

    description: str
    use_color: bool
    expected_text: str
    expected_fault_count: int
    expected_warning_count: int
