"""Evaluate selected Python-authored rules over serialized Web facts."""

from __future__ import annotations

from pathlib import Path

from fensu.config.models import Config
from fensu.evaluation.classes.custom_rule_coverage_evaluator import CustomRuleCoverageEvaluator
from fensu.evaluation.classes.web_rule_executor import WebRuleExecutor
from fensu.evaluation.classes.web_rule_result_cache import WebRuleResultCache
from fensu.rules.authoring.models import ArchitectureGraph, ProjectTree, RuleSpec, WebWorkspaceFacts
from fensu.rules.authoring.types import RuleKind
from fensu.rules.catalog.models import RuleSelection
from fensu.rules.roles.types import RoleCode


def evaluate_web_custom_rules(
    *,
    root: Path,
    tree: ProjectTree,
    graph: ArchitectureGraph,
    workspace: WebWorkspaceFacts,
    config: Config,
    selection: RuleSelection,
    include_warnings: bool,
) -> tuple[list[dict[str, object]], list[dict[str, str]], tuple[str, ...], tuple[str, ...], bool]:
    """Run selected typed custom rules and serialize deterministic findings."""

    blocking: tuple[RuleSpec, ...] = tuple(
        rule for rule in selection.blocking if rule.kind is RuleKind.CUSTOM
    )
    warnings: tuple[RuleSpec, ...] = (
        tuple(rule for rule in selection.warnings if rule.kind is RuleKind.CUSTOM)
        if include_warnings
        else ()
    )
    cacheable: bool = all(rule.cacheable is True for rule in (*blocking, *warnings))
    cache: WebRuleResultCache = WebRuleResultCache(
        root=root,
        config=config,
        fact_schema=workspace.schema_version,
        parser_contract=workspace.parser_contract,
        enabled=config.cache.enabled and cacheable,
    )
    findings: list[dict[str, object]] = []
    observations: list[dict[str, str]] = []
    coverage_rule: RuleSpec | None = next(
        (
            rule
            for rule in (*selection.blocking, *(selection.warnings if include_warnings else ()))
            if rule.code == RoleCode.CUSTOM_RULE_TEST_COVERAGE
        ),
        None,
    )
    coverage_warning: bool = coverage_rule in selection.warnings
    if coverage_rule is not None:
        findings.extend(
            CustomRuleCoverageEvaluator.evaluate(
                root=root,
                config=config,
                registrations=selection.custom_registrations,
                rule=coverage_rule,
                warning=coverage_warning,
            )
        )
    for warning, rules in ((False, blocking), (True, warnings)):
        for rule in rules:
            current_findings: list[dict[str, object]]
            current_observations: list[dict[str, str]]
            current_findings, current_observations = WebRuleExecutor.execute(
                root=root,
                tree=tree,
                graph=graph,
                workspace=workspace,
                config=config,
                rule=rule,
                warning=warning,
                cache=cache,
            )
            findings.extend(current_findings)
            observations.extend(current_observations)
    cache.publish()
    findings.sort(
        key=lambda item: (
            str(item["path"]),
            int(item["line"] or 0),
            int(item["column"] or 0),
            str(item["code"]),
            str(item["message"]),
        )
    )
    unique_observations: list[tuple[tuple[str, str], ...]] = sorted(
        {tuple(sorted(item.items())) for item in observations},
        key=repr,
    )
    return (
        findings,
        [dict(item) for item in unique_observations],
        tuple(rule.code for rule in blocking)
        + ((coverage_rule.code,) if coverage_rule is not None and not coverage_warning else ()),
        tuple(rule.code for rule in warnings)
        + ((coverage_rule.code,) if coverage_warning and coverage_rule is not None else ()),
        cacheable,
    )
