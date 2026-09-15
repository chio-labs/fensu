"""Evaluate selected Python-authored rules over serialized Rust facts."""

from __future__ import annotations

from pathlib import Path

from fensu.config.models import Config
from fensu.evaluation.classes.rust_rule_executor import RustRuleExecutor
from fensu.evaluation.classes.rust_rule_result_cache import RustRuleResultCache
from fensu.rules.authoring.models import ProjectTree, RuleSpec, RustWorkspaceFacts
from fensu.rules.authoring.types import RuleKind
from fensu.rules.catalog.models import RuleSelection


def evaluate_rust_custom_rules(
    *,
    root: Path,
    tree: ProjectTree,
    workspace: RustWorkspaceFacts,
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
    cache: RustRuleResultCache = RustRuleResultCache(
        root=root,
        config=config,
        fact_schema=workspace.schema_version,
        parser_contract=workspace.parser_contract,
        enabled=config.cache.enabled and cacheable,
    )
    findings: list[dict[str, object]] = []
    observations: list[dict[str, str]] = []
    for warning, rules in ((False, blocking), (True, warnings)):
        for rule in rules:
            current_findings: list[dict[str, object]]
            current_observations: list[dict[str, str]]
            current_findings, current_observations = RustRuleExecutor.execute(
                root=root,
                tree=tree,
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
        tuple(rule.code for rule in blocking),
        tuple(rule.code for rule in warnings),
        cacheable,
    )
