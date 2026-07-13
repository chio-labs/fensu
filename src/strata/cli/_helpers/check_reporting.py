"""Assemble the rendered check report and threshold observations."""

from __future__ import annotations

from strata.discovery.models import DiscoveredTree
from strata.evaluation.models import EvaluationResult
from strata.reporting.main.render import render
from strata.reporting.models import RenderedReport


def render_check_result(
    *, result: EvaluationResult, tree: DiscoveredTree, use_color: bool
) -> RenderedReport:
    """Render check faults with effective threshold-override observations."""

    return render(
        faults=result.faults,
        root=tree.repo_root.path,
        use_color=use_color,
        applied_exception_count=result.applied_exception_count,
        threshold_override_uses=result.threshold_override_uses,
    )
