"""Build evaluation-scoped project analysis."""

from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.project_analysis import build_project_analysis
from strata.evaluation.types import EvaluationProjectAnalysis


def build_evaluation_project(*, tree: DiscoveredTree) -> EvaluationProjectAnalysis:
    """Return one shared project-analysis snapshot for an evaluation."""

    return build_project_analysis(tree=tree)
