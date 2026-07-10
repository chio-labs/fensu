"""Public report renderer."""

from __future__ import annotations

from pathlib import Path

from strata.reporting.core.helpers.text import render_text
from strata.reporting.core.models import RenderedReport
from strata.rules.authoring.models import Fault


def render(
    *,
    faults: tuple[Fault, ...],
    root: Path,
    use_color: bool = False,
    applied_exception_count: int = 0,
) -> RenderedReport:
    """Render evaluation faults for terminal output."""

    return RenderedReport(
        text=render_text(
            faults=faults,
            root=root,
            use_color=use_color,
            applied_exception_count=applied_exception_count,
        ),
        fault_count=len(faults),
        applied_exception_count=applied_exception_count,
    )
