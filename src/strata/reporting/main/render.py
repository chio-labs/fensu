"""Public report renderer."""

from __future__ import annotations

from pathlib import Path

from strata.evaluation.models import ThresholdOverrideUse
from strata.reporting.helpers.text import render_text
from strata.reporting.models import RenderedReport
from strata.rules.authoring.models import Fault


def render(
    *,
    faults: tuple[Fault, ...],
    root: Path,
    use_color: bool = False,
    applied_exception_count: int = 0,
    threshold_override_uses: tuple[ThresholdOverrideUse, ...] = (),
) -> RenderedReport:
    """Render evaluation faults for terminal output."""

    return RenderedReport(
        text=render_text(
            faults=faults,
            root=root,
            use_color=use_color,
            applied_exception_count=applied_exception_count,
            threshold_override_uses=threshold_override_uses,
        ),
        fault_count=len(faults),
        applied_exception_count=applied_exception_count,
    )
