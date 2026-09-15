"""Evaluate typed project rules without selecting or parsing a source anchor."""

from __future__ import annotations

from pathlib import Path

from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree, RepoRoot
from fensu.evaluation._helpers.rule_exceptions import suppress_project_faults
from fensu.evaluation.classes.project_rule_context import ProjectRuleContext
from fensu.evaluation.constants import PROJECT_REQUESTER_NAME
from fensu.evaluation.exceptions import RuleCallbackUnavailableError
from fensu.evaluation.models import ProjectEvaluation, RuleExceptionKey, ThresholdOverrideUse
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.models import Fault, Project, RuleSpec


def evaluate_project_rules(
    *,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    tree: DiscoveredTree,
    analysis: EvaluationProjectAnalysis,
) -> ProjectEvaluation | None:
    """Invoke each selected project rule once at a source-independent boundary."""

    if not ruleset and not warning_rules:
        return None
    faults: list[Fault] = []
    warnings: list[Fault] = []
    applied: set[RuleExceptionKey] = set()
    threshold_override_uses: set[ThresholdOverrideUse] = set()
    requester: Path = tree.repo_root.path / PROJECT_REQUESTER_NAME
    project_root: RepoRoot = tree.repo_root if tree.project_root is None else tree.project_root
    for rules, output in ((ruleset, faults), (warning_rules, warnings)):
        for rule in rules:
            if rule.check is None:
                raise RuleCallbackUnavailableError(f"Project rule {rule.code} has no callback.")
            ctx: ProjectRuleContext = ProjectRuleContext(
                tree=tree,
                analysis=analysis,
                config=config,
                rule=rule,
            )
            rule_faults: list[Fault] = rule.check(
                **{
                    rule.subject_parameter or "project": Project(),
                    rule.context_parameter or "ctx": ctx,
                }
            )
            retained, used = suppress_project_faults(
                faults=rule_faults,
                config=config,
                repo_root=project_root.path,
                tree=tree,
                analysis=analysis,
                requester=requester,
            )
            output.extend(retained)
            applied.update(used)
            threshold_override_uses.update(ctx.threshold_override_uses)
    return ProjectEvaluation(
        faults=tuple(faults),
        warnings=tuple(warnings),
        applied_exception_keys=tuple(
            sorted(applied, key=lambda key: (key.rule, key.path, key.symbol or ""))
        ),
        dependencies=analysis.dependencies_for(requester=requester),
        threshold_override_uses=tuple(
            sorted(
                threshold_override_uses,
                key=lambda use: (
                    use.repository_path,
                    use.threshold.value,
                    use.override_order,
                ),
            )
        ),
    )
