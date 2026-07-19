"""Rule execution helpers."""

from __future__ import annotations

import ast
from typing import cast

from fensu.analysis.types import ProjectAnalysis
from fensu.config.models import Config
from fensu.discovery.models import ProjectLayout, RepoRoot
from fensu.evaluation.classes.rule_context import EvaluationRuleContext
from fensu.evaluation.exceptions import ModuleUnavailableError
from fensu.evaluation.models import ParsedModule, ThresholdOverrideUse
from fensu.instrumentation.constants import OPERATION_COUNTERS, PYTHON_CORE_RULE_CALLBACK_OPERATION
from fensu.rules.authoring.models import Fault, RuleSpec
from fensu.rules.authoring.types import RuleKind


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
    if rule.kind is RuleKind.CORE:
        OPERATION_COUNTERS.record(operation=PYTHON_CORE_RULE_CALLBACK_OPERATION)
    return rule.check(module=module, ctx=ctx)
