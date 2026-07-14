"""Rule execution helpers."""

from __future__ import annotations

import ast
from typing import cast

from strata.analysis.types import ProjectAnalysis
from strata.config.models import Config
from strata.discovery.models import ProjectLayout, RepoRoot
from strata.evaluation.classes.rule_context import EvaluationRuleContext
from strata.evaluation.exceptions import ModuleUnavailableError
from strata.evaluation.models import ParsedModule, ThresholdOverrideUse
from strata.rules.authoring.models import Fault, RuleSpec


class _UnavailableModule:
    """Fail-loud placeholder handed to rules that declare no raw-AST use."""

    def __getattr__(self, name: str) -> object:
        raise ModuleUnavailableError(
            "This rule declared no raw-AST use but read the module parameter; "
            "remove the module access or drop the leading 'del module'."
        )


_UNAVAILABLE_MODULE: ast.Module = cast(ast.Module, _UnavailableModule())


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
    module: ast.Module = (
        parsed_module.syntax_artifacts.module if rule.uses_module else _UNAVAILABLE_MODULE
    )
    return rule.check(module=module, ctx=ctx)
