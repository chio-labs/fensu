"""Build evaluation-scoped project analysis."""

from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.helpers.project_analysis import build_project_analysis
from strata.evaluation.core.types import EvaluationProjectAnalysis


def build_evaluation_project(*, tree: DiscoveredTree) -> EvaluationProjectAnalysis:
    """Return one shared project-analysis snapshot for an evaluation."""

    return build_project_analysis(tree=tree)
