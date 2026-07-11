"""Evaluate a ruleset over a discovered tree."""

from __future__ import annotations

from strata.config.core.exceptions import ConfigError
from strata.config.core.models import Config
from strata.discovery.core.main.route import families_for_scope
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.helpers.collection import sort_faults
from strata.evaluation.core.helpers.execution import execute_rule
from strata.evaluation.core.helpers.project_analysis import build_project_analysis
from strata.evaluation.core.helpers.rule_exceptions import (
    configured_exception_keys,
    stale_exception_error,
    suppress_faults,
)
from strata.evaluation.core.models import EvaluationResult, ParsedModule, RuleExceptionKey
from strata.evaluation.core.types import EvaluationProjectAnalysis
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
    applied_exceptions: set[RuleExceptionKey] = set()
    has_exceptions: bool = bool(config.rule_exceptions)
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)
    for scoped_file in tree.files:
        parsed_module: ParsedModule = project.parsed_module(scoped_file)
        file_cache: dict[str, object] = {}
        applicable_families: frozenset[Family] = families_for_scope(scoped_file=scoped_file)
        for rule in ruleset:
            if rule.family != Family.CUSTOM and rule.family not in applicable_families:
                continue
            rule_faults: list[Fault] = execute_rule(
                rule=rule,
                parsed_module=parsed_module,
                config=config,
                repo_root=tree.repo_root,
                project=project,
                file_cache=file_cache,
            )
            if has_exceptions:
                retained, applied = suppress_faults(
                    faults=rule_faults,
                    parsed_module=parsed_module,
                    config=config,
                    repo_root=tree.repo_root.path,
                )
                faults.extend(retained)
                applied_exceptions.update(applied)
            else:
                faults.extend(rule_faults)
    configured: frozenset[RuleExceptionKey] = configured_exception_keys(config)
    stale_error: ConfigError | None = stale_exception_error(
        configured=configured, applied=frozenset(applied_exceptions)
    )
    if stale_error is not None:
        raise stale_error
    return EvaluationResult(
        faults=sort_faults(faults=faults, repo_root=tree.repo_root.path),
        applied_exception_count=len(applied_exceptions),
    )
