"""Evaluate one discovered file through the shared uncached boundary."""

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree, ScopedFile
from strata.evaluation._helpers.file_evaluation import evaluate_file
from strata.evaluation.models import FileEvaluation
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import RuleSpec


def evaluate_discovered_file(
    *,
    scoped_file: ScopedFile,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
) -> FileEvaluation:
    """Return unrendered output and observations for one discovered source file."""

    return evaluate_file(
        scoped_file=scoped_file,
        ruleset=ruleset,
        warning_rules=warning_rules,
        config=config,
        tree=tree,
        project=project,
    )
