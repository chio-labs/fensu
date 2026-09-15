"""Evaluate selected cross-target repository custom rules exactly once."""

from pathlib import Path

from fensu.config.models import Config
from fensu.evaluation.classes.repository_rule_evaluator import (
    RepositoryRuleEvaluator,
)
from fensu.evaluation.classes.repository_rule_target import RepositoryRuleTargetView
from fensu.evaluation.types import RepositoryEvaluation
from fensu.rules.catalog.models import RuleSelection


def evaluate_repository_custom_rules(
    *,
    root: Path,
    targets: tuple[RepositoryRuleTargetView, ...],
    config: Config,
    selection: RuleSelection,
    include_warnings: bool,
) -> RepositoryEvaluation:
    """Run repository rules and return deterministic host transport values."""

    return RepositoryRuleEvaluator.evaluate(
        root=root,
        targets=targets,
        config=config,
        selection=selection,
        include_warnings=include_warnings,
    )
