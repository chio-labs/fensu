"""Evaluate one discovered file through the shared uncached boundary."""

from strata.config.core.models import Config
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from strata.evaluation.core.helpers.file_evaluation import evaluate_file
from strata.evaluation.core.models import FileEvaluation
from strata.evaluation.core.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import RuleSpec


def evaluate_discovered_file(
    *,
    scoped_file: ScopedFile,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
) -> FileEvaluation:
    """Return unrendered output and observations for one discovered source file."""

    return evaluate_file(
        scoped_file=scoped_file,
        ruleset=ruleset,
        config=config,
        tree=tree,
        project=project,
    )
