"""Evaluate a ruleset over a discovered tree."""

from __future__ import annotations

from strata.config.core.models import Config
from strata.discovery.core.main.route import families_for_scope
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from strata.evaluation.core.helpers.collection import sort_faults
from strata.evaluation.core.helpers.execution import execute_rule
from strata.evaluation.core.helpers.parsing import parse_scoped_file
from strata.evaluation.core.models import EvaluationResult, ParsedModule
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family


def evaluate(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
) -> EvaluationResult:
    """Evaluate selected rules over discovered Python files."""

    faults: list[Fault] = []
    for scoped_file in tree.files:
        parsed_module: ParsedModule = _parse_file(scoped_file=scoped_file)
        for rule in ruleset:
            if rule.family != Family.CUSTOM and rule.family not in families_for_scope(
                scoped_file=scoped_file
            ):
                continue
            faults.extend(
                execute_rule(
                    rule=rule,
                    parsed_module=parsed_module,
                    config=config,
                    repo_root=tree.repo_root,
                )
            )
    return EvaluationResult(faults=sort_faults(faults=faults, repo_root=tree.repo_root.path))


def _parse_file(*, scoped_file: ScopedFile) -> ParsedModule:
    return parse_scoped_file(scoped_file)
