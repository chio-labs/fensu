"""Public report renderer."""

from __future__ import annotations

from pathlib import Path

from fensu.evaluation.models import ThresholdOverrideUse
from fensu.reporting._helpers.text import render_text
from fensu.reporting.models import RenderedReport
from fensu.rules.authoring.models import Fault


def render(
    *,
    faults: tuple[Fault, ...],
    warnings: tuple[Fault, ...] = (),
    root: Path,
    use_color: bool = False,
    show_warnings: bool = False,
    evaluation_summary: str | None = None,
    applied_exception_count: int = 0,
    threshold_override_uses: tuple[ThresholdOverrideUse, ...] = (),
) -> RenderedReport:
    """Render evaluation faults for terminal output."""

    return RenderedReport(
        text=render_text(
            faults=faults,
            warnings=warnings,
            root=root,
            use_color=use_color,
            show_warnings=show_warnings,
            evaluation_summary=evaluation_summary,
            applied_exception_count=applied_exception_count,
            threshold_override_uses=threshold_override_uses,
        ),
        fault_count=len(faults),
        warning_count=len(warnings),
        applied_exception_count=applied_exception_count,
    )
