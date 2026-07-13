"""Assemble the rendered check report and threshold observations."""

from __future__ import annotations

from strata.discovery.models import DiscoveredTree
from strata.evaluation.models import EvaluationResult
from strata.reporting.main.render import render
from strata.reporting.models import RenderedReport


def render_check_result(
    *, result: EvaluationResult, tree: DiscoveredTree, use_color: bool, show_warnings: bool = False
) -> RenderedReport:
    """Render check faults with effective threshold-override observations."""

    return render(
        faults=result.faults,
        warnings=result.warnings,
        root=tree.repo_root.path,
        use_color=use_color,
        show_warnings=show_warnings,
        applied_exception_count=result.applied_exception_count,
        threshold_override_uses=result.threshold_override_uses,
    )
