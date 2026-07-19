"""Build evaluation-scoped project analysis."""

from fensu.discovery.models import DiscoveredTree
from fensu.evaluation._helpers.project_analysis import build_project_analysis
from fensu.evaluation.types import EvaluationProjectAnalysis


def build_evaluation_project(*, tree: DiscoveredTree) -> EvaluationProjectAnalysis:
    """Return one shared project-analysis snapshot for an evaluation."""

    return build_project_analysis(tree=tree)
