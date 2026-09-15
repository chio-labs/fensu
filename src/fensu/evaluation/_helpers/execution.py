"""Rule execution helpers."""

from __future__ import annotations

import ast
from typing import cast

from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree, ProjectLayout, RepoRoot
from fensu.evaluation.classes.rule_context import EvaluationRuleContext
from fensu.evaluation.exceptions import (
    ModuleUnavailableError,
    NativeCoreCallbackError,
    RuleCallbackUnavailableError,
)
from fensu.evaluation.models import ParsedModule, ThresholdOverrideUse
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.models import Fault, RuleSpec
from fensu.rules.authoring.subjects import File, ProjectPath
from fensu.rules.authoring.types import RuleCheck, RuleKind, RuleSubjectKind


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
    project: EvaluationProjectAnalysis,
    file_cache: dict[str, object],
    threshold_override_uses: list[ThresholdOverrideUse],
    tree: DiscoveredTree,
) -> list[Fault]:
    """Run one rule against one parsed module."""

    check: RuleCheck | None = rule.check
    if check is None:
        if rule.kind in {RuleKind.CORE, RuleKind.PACK}:
            raise NativeCoreCallbackError(
                f"Native evaluation returned no result for selected core rule {rule.code}."
            )
        raise RuleCallbackUnavailableError(f"Custom rule {rule.code} has no callback.")
    ctx: EvaluationRuleContext = EvaluationRuleContext(
        parsed_module=parsed_module,
        config=config,
        repo_root=repo_root,
        layout=layout,
        rule=rule,
        project=project,
        file_cache=file_cache,
        threshold_override_uses=threshold_override_uses,
        tree=tree,
    )
    if rule.subject_kind is RuleSubjectKind.FILE:
        return check(
            **{
                rule.subject_parameter or "file": File(
                    path=ProjectPath(
                        parsed_module.scoped_file.path.relative_to(repo_root.path).as_posix()
                    )
                ),
                rule.context_parameter or "ctx": ctx,
            }
        )
    if rule.subject_kind is RuleSubjectKind.PROJECT:
        raise RuleCallbackUnavailableError(
            f"Project rule {rule.code} reached the file execution boundary."
        )
    module: ast.Module = (
        parsed_module.syntax_artifacts.module if rule.uses_module else _UNAVAILABLE_MODULE
    )
    return check(module=module, ctx=ctx)
