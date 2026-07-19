"""Evaluate one custom rule through the ordinary Fensu pipeline."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.main._resolve_rule_spec import resolve_rule_spec
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import RuleCheck
from fensu.rules.catalog.main._check_module_use import check_uses_module
from fensu.rules.testing._helpers.remapping import remap_rule_result
from fensu.rules.testing._helpers.repository import (
    build_harness_config,
    write_harness_repository,
)
from fensu.rules.testing._helpers.validation import validate_rule_case
from fensu.rules.testing.models import RuleCase, RuleResult


def evaluate_rule(*, rule: RuleCheck | RuleSpec, test_case: RuleCase) -> RuleResult:
    """Evaluate a decorated rule against one isolated real-pipeline case."""

    unresolved_rule: RuleSpec = resolve_rule_spec(value=rule)
    resolved_rule: RuleSpec = replace(
        unresolved_rule,
        uses_module=check_uses_module(check=unresolved_rule.check),
    )
    validate_rule_case(test_case=test_case)
    config: Config = build_harness_config(test_case=test_case)
    with TemporaryDirectory(prefix="fensu-rule-") as directory:
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
