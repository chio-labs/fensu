"""Evaluate one custom rule through the ordinary Strata pipeline."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.main._resolve_rule_spec import resolve_rule_spec
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleCheck
from strata.rules.catalog.main._check_module_use import check_uses_module
from strata.rules.testing._helpers.remapping import remap_rule_result
from strata.rules.testing._helpers.repository import (
    build_harness_config,
    write_harness_repository,
)
from strata.rules.testing._helpers.validation import validate_rule_case
from strata.rules.testing.models import RuleCase, RuleResult


def evaluate_rule(*, rule: RuleCheck | RuleSpec, test_case: RuleCase) -> RuleResult:
    """Evaluate a decorated rule against one isolated real-pipeline case."""

    unresolved_rule: RuleSpec = resolve_rule_spec(value=rule)
    resolved_rule: RuleSpec = replace(
        unresolved_rule,
        uses_module=check_uses_module(check=unresolved_rule.check),
    )
    validate_rule_case(test_case=test_case)
    config: Config = build_harness_config(test_case=test_case)
    with TemporaryDirectory(prefix="strata-rule-") as directory:
        repo_root: Path = Path(directory).resolve()
        write_harness_repository(repo_root=repo_root, test_case=test_case, config=config)
        tree: DiscoveredTree = discover_files(config=config, repo_root=repo_root)
        result: EvaluationResult = evaluate(
            tree=tree,
            ruleset=(resolved_rule,),
            config=config,
        )
        return remap_rule_result(
            faults=result.faults,
            dependencies=result.dependencies,
            repo_root=repo_root,
        )
