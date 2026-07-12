"""Evaluate one discovered file through the uncached result boundary."""

from __future__ import annotations

from strata.config.core.models import Config
from strata.discovery.core.main.route import families_for_scope
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from strata.evaluation.core.helpers.execution import execute_rule
from strata.evaluation.core.helpers.rule_exceptions import suppress_faults
from strata.evaluation.core.models import FileEvaluation, ParsedModule, RuleExceptionKey
from strata.evaluation.core.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family


def evaluate_file(
    *,
    scoped_file: ScopedFile,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
) -> FileEvaluation:
    """Return unrendered output and observed inputs for one source file."""

    parsed_module: ParsedModule = project.parsed_module(scoped_file)
    faults: list[Fault] = []
    applied_exceptions: set[RuleExceptionKey] = set()
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
            layout=tree.layout,
            project=project,
            file_cache=file_cache,
        )
        if config.rule_exceptions:
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
    return FileEvaluation(
        path=scoped_file.path,
        source_fingerprint=parsed_module.source_fingerprint,
        faults=tuple(faults),
        applied_exception_keys=tuple(
            sorted(applied_exceptions, key=lambda item: (item.rule, item.path, item.symbol))
        ),
        dependencies=project.dependencies_for(requester=scoped_file.path),
    )
