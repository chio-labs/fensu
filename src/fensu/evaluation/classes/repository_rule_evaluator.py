"""Repository custom-rule selection, execution, and policy application."""

from __future__ import annotations

import json
from pathlib import Path

from fensu.config.main.matches_path_pattern import matches_path_pattern
from fensu.config.models import Config, RuleExceptionEntry, RuleIgnoreEntry
from fensu.config.types import AnalyzerId
from fensu.evaluation.classes.repository_rule_executor import RepositoryRuleExecutor
from fensu.evaluation.classes.repository_rule_result_cache import RepositoryRuleResultCache
from fensu.evaluation.classes.repository_rule_target import RepositoryRuleTargetView
from fensu.evaluation.exceptions import RepositoryRuleError
from fensu.evaluation.types import RepositoryEvaluation
from fensu.rules.authoring.main.matches_rule_selector import matches_rule_selector
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import RuleKind
from fensu.rules.catalog.models import RuleSelection


class RepositoryRuleEvaluator:
    """Evaluate selected repository rules over explicit target handles."""

    @staticmethod
    def evaluate(
        *,
        root: Path,
        targets: tuple[RepositoryRuleTargetView, ...],
        config: Config,
        selection: RuleSelection,
        include_warnings: bool,
    ) -> RepositoryEvaluation:
        """Run rules, apply repository policy, and return canonical host output."""

        blocking: tuple[RuleSpec, ...] = tuple(
            rule for rule in selection.blocking if rule.kind is RuleKind.CUSTOM
        )
        warnings: tuple[RuleSpec, ...] = (
            tuple(rule for rule in selection.warnings if rule.kind is RuleKind.CUSTOM)
            if include_warnings
            else ()
        )
        evaluated: tuple[RuleSpec, ...] = (*blocking, *warnings)
        cacheable: bool = all(rule.cacheable is True for rule in evaluated)
        cache: RepositoryRuleResultCache = RepositoryRuleResultCache(
            root=root,
            config=config,
            registry_identity=RepositoryRuleEvaluator._registry_identity(targets=targets),
            enabled=config.cache.enabled and cacheable,
        )
        findings, observations = RepositoryRuleEvaluator._execute(
            root=root,
            targets=targets,
            config=config,
            blocking=blocking,
            warnings=warnings,
            cache=cache,
        )
        visible, applied = RepositoryRuleEvaluator._apply_policy(
            findings=findings, evaluated=evaluated, config=config
        )
        return (
            visible,
            RepositoryRuleEvaluator._unique_observations(observations=observations),
            tuple(rule.code for rule in blocking),
            tuple(rule.code for rule in warnings),
            cacheable,
            applied,
            cache.stats,
        )

    @staticmethod
    def _registry_identity(*, targets: tuple[RepositoryRuleTargetView, ...]) -> str:
        values: list[dict[str, object]] = []
        for target in targets:
            analyzer: AnalyzerId = target.identity.analyzer
            values.append(
                {
                    "analyzer": analyzer.value,
                    "name": target.identity.name,
                    "root": target.identity.root.value,
                    "python": (
                        [target.python.schema_version, target.python.parser_contract]
                        if analyzer is AnalyzerId.PYTHON
                        else None
                    ),
                    "rust": (
                        [target.rust.schema_version, target.rust.parser_contract]
                        if analyzer is AnalyzerId.RUST
                        else None
                    ),
                    "web": (
                        [target.web.schema_version, target.web.parser_contract]
                        if analyzer in {AnalyzerId.TYPESCRIPT, AnalyzerId.SVELTE}
                        else None
                    ),
                }
            )
        return json.dumps(values, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _execute(
        *,
        root: Path,
        targets: tuple[RepositoryRuleTargetView, ...],
        config: Config,
        blocking: tuple[RuleSpec, ...],
        warnings: tuple[RuleSpec, ...],
        cache: RepositoryRuleResultCache,
    ) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
        findings: list[dict[str, object]] = []
        observations: list[dict[str, str]] = []
        for warning, rules in ((False, blocking), (True, warnings)):
            for rule in rules:
                current, dependencies = RepositoryRuleExecutor.execute(
                    root=root,
                    base_targets=targets,
                    config=config,
                    rule=rule,
                    warning=warning,
                    cache=cache,
                )
                findings.extend(current)
                observations.extend(dependencies)
        return findings, observations

    @staticmethod
    def _apply_policy(
        *, findings: list[dict[str, object]], evaluated: tuple[RuleSpec, ...], config: Config
    ) -> tuple[list[dict[str, object]], int]:
        visible: list[dict[str, object]] = []
        applied: set[tuple[str, str]] = set()
        for finding in findings:
            if RepositoryRuleEvaluator._ignored(finding=finding, entries=config.rule_ignores):
                continue
            exception: RuleExceptionEntry | None = next(
                (
                    item
                    for item in config.rule_exceptions
                    if item.rule == finding["code"] and item.path == finding["path"]
                ),
                None,
            )
            if exception is None:
                visible.append(finding)
            else:
                applied.add((exception.rule, exception.path))
        RepositoryRuleEvaluator._validate_exceptions(
            exceptions=config.rule_exceptions, evaluated=evaluated, applied=applied
        )
        visible.sort(
            key=lambda item: (
                str(item["path"]),
                int(item["line"] or 0),
                int(item["column"] or 0),
                str(item["code"]),
                str(item["message"]),
            )
        )
        return visible, len(applied)

    @staticmethod
    def _validate_exceptions(
        *,
        exceptions: tuple[RuleExceptionEntry, ...],
        evaluated: tuple[RuleSpec, ...],
        applied: set[tuple[str, str]],
    ) -> None:
        evaluated_codes: frozenset[str] = frozenset(rule.code for rule in evaluated)
        stale: RuleExceptionEntry | None = next(
            (
                item
                for item in exceptions
                if item.rule in evaluated_codes and (item.rule, item.path) not in applied
            ),
            None,
        )
        if stale is not None:
            raise RepositoryRuleError(
                f"Rule exception no longer matches a fault: {stale.rule} {stale.path}. "
                f"Remove it or update its scope. Reason: {stale.reason}"
            )

    @staticmethod
    def _ignored(*, finding: dict[str, object], entries: tuple[RuleIgnoreEntry, ...]) -> bool:
        code: str = str(finding["code"])
        path: str = str(finding["path"])
        for entry in entries:
            selector_matches: bool = any(
                matches_rule_selector(code=code, selector=selector) for selector in entry.rules
            )
            if selector_matches and matches_path_pattern(patterns=entry.paths, path=path):
                return True
        return False

    @staticmethod
    def _unique_observations(*, observations: list[dict[str, str]]) -> list[dict[str, str]]:
        unique: list[tuple[tuple[str, str], ...]] = sorted(
            {tuple(sorted(item.items())) for item in observations}, key=repr
        )
        return [dict(item) for item in unique]
