"""Single-invocation execution for repository-subject custom rules."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from fensu.config.models import Config
from fensu.evaluation.classes.repository_rule_context import RepositoryRuleContext
from fensu.evaluation.classes.repository_rule_result_cache import RepositoryRuleResultCache
from fensu.evaluation.classes.repository_rule_target import RepositoryRuleTargetView
from fensu.evaluation.classes.repository_rule_targets import RepositoryRuleTargets
from fensu.evaluation.exceptions import RepositoryRuleError
from fensu.rules.authoring.models import Fault, Repository, RuleSpec


class RepositoryRuleExecutor:
    """Execute one repository rule exactly once with observed target handles."""

    @staticmethod
    def execute(
        *,
        root: Path,
        base_targets: tuple[RepositoryRuleTargetView, ...],
        config: Config,
        rule: RuleSpec,
        warning: bool,
        cache: RepositoryRuleResultCache,
    ) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
        """Return serialized findings and target-qualified dependencies."""

        base_collection: RepositoryRuleTargets = RepositoryRuleTargets(values=base_targets)
        cached: tuple[list[dict[str, object]], list[dict[str, str]]] | None = cache.read(
            rule=rule, targets=base_collection
        )
        if cached is not None:
            return cached
        observations: list[dict[str, str]] = []
        targets: RepositoryRuleTargets = RepositoryRuleTargets(
            values=tuple(
                target.observed(
                    observations=observations,
                    allowed_analyzers=frozenset(rule.analyzers),
                )
                for target in base_targets
            )
        )
        context: RepositoryRuleContext = RepositoryRuleContext(
            root=root, config=config, rule=rule, targets=targets
        )
        faults: object = (
            rule.check(
                **{
                    rule.subject_parameter or "repository": Repository(),
                    rule.context_parameter or "ctx": context,
                }
            )
            if rule.check is not None
            else []
        )
        findings: list[dict[str, object]] = RepositoryRuleExecutor._serialize(
            root=root, rule=rule, faults=faults, warning=warning
        )
        cache.write(rule=rule, findings=findings, dependencies=observations)
        return findings, observations

    @staticmethod
    def _serialize(
        *, root: Path, rule: RuleSpec, faults: object, warning: bool
    ) -> list[dict[str, object]]:
        if not isinstance(faults, list) or any(not isinstance(item, Fault) for item in faults):
            raise RepositoryRuleError(f"Repository custom rule {rule.code} must return list[Fault]")
        values: list[dict[str, object]] = []
        for fault in cast("list[Fault]", faults):
            if fault.code != rule.code:
                raise RepositoryRuleError(
                    f"Repository custom rule {rule.code} returned fault code {fault.code}"
                )
            path: Path = fault.path.resolve()
            if not path.is_relative_to(root):
                raise RepositoryRuleError(
                    f"Repository custom rule {rule.code} returned a path outside the repository"
                )
            values.append(
                {
                    "code": fault.code,
                    "path": path.relative_to(root).as_posix(),
                    "line": fault.line,
                    "column": fault.column,
                    "symbol": None,
                    "message": fault.message,
                    "remediation": fault.remediation,
                    "severity": "warning" if warning else "blocking",
                }
            )
        return values
