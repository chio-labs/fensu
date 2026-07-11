"""Rule execution helpers."""

from __future__ import annotations

from strata.analysis.core.types import ProjectAnalysis
from strata.config.core.models import Config
from strata.discovery.core.models import RepoRoot
from strata.evaluation.core.classes.rule_context import EvaluationRuleContext
from strata.evaluation.core.models import ParsedModule
from strata.rules.authoring.models import Fault, RuleSpec


def execute_rule(
    *,
    rule: RuleSpec,
    parsed_module: ParsedModule,
    config: Config,
    repo_root: RepoRoot,
    project: ProjectAnalysis,
    file_cache: dict[str, object],
) -> list[Fault]:
    """Run one rule against one parsed module."""

    ctx: EvaluationRuleContext = EvaluationRuleContext(
        parsed_module=parsed_module,
        config=config,
        repo_root=repo_root,
        rule=rule,
        project=project,
        file_cache=file_cache,
    )
    return rule.check(module=parsed_module.module, ctx=ctx)
