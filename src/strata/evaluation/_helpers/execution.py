"""Rule execution helpers."""

from __future__ import annotations

from strata.analysis.types import ProjectAnalysis
from strata.config.models import Config
from strata.discovery.models import ProjectLayout, RepoRoot
from strata.evaluation.classes.rule_context import EvaluationRuleContext
from strata.evaluation.models import ParsedModule, ThresholdOverrideUse
from strata.rules.authoring.models import Fault, RuleSpec


def execute_rule(
    *,
    rule: RuleSpec,
    parsed_module: ParsedModule,
    config: Config,
    repo_root: RepoRoot,
    layout: ProjectLayout,
    project: ProjectAnalysis,
    file_cache: dict[str, object],
    threshold_override_uses: list[ThresholdOverrideUse],
) -> list[Fault]:
    """Run one rule against one parsed module."""

    ctx: EvaluationRuleContext = EvaluationRuleContext(
        parsed_module=parsed_module,
        config=config,
        repo_root=repo_root,
        layout=layout,
        rule=rule,
        project=project,
        file_cache=file_cache,
        threshold_override_uses=threshold_override_uses,
    )
    return rule.check(module=parsed_module.module, ctx=ctx)
