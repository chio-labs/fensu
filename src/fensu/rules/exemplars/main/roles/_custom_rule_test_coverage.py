"""Public custom routing equivalent of source-owned coverage policy."""

import ast
from pathlib import Path

from fensu import Fault, RuleContext, ScopeName, Threshold
from fensu.analysis.main.associate_rule_tests import associate_rule_tests
from fensu.analysis.models import EvaluateRuleCallFact, RuleTestAssociationFact
from fensu.analysis.types import Analysis
from fensu.discovery.constants import INIT_MODULE_NAME
from fensu.rules.authoring.models import CustomRuleRegistration
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule


@equivalent_rule(
    core_code="FFR707",
    code="XCR707",
    slug="custom-rule-test-coverage-equivalent",
)
def custom_rule_test_coverage_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR707 through public registration and project-analysis APIs."""

    del module
    registrations: tuple[CustomRuleRegistration, ...] = ctx.custom_rule_registrations()
    minimum: int = ctx.threshold(name=Threshold.MIN_CUSTOM_RULE_TEST_CASES)
    if not registrations or minimum == 0:
        return []
    modules: dict[str, Analysis] = {}
    calls: list[EvaluateRuleCallFact] = []
    for test_root in ctx.scope_roots(ScopeName.TEST):
        for path in ctx.project.glob(
            requester=ctx.path,
            path=test_root,
            pattern="*.py",
            recursive=True,
        ):
            analysis: Analysis | None = ctx.project.analysis(requester=ctx.path, path=path)
            if analysis is None:
                continue
            modules[_module_name(path=path, import_root=test_root.parent)] = analysis
            calls.extend(analysis.facts.evaluate_rule_calls())
    source_analysis: Analysis | None = ctx.project.analysis(requester=ctx.path, path=ctx.path)
    if source_analysis is not None:
        for registration in registrations:
            modules[registration.module_name] = source_analysis
    associations: tuple[RuleTestAssociationFact, ...] = associate_rule_tests(
        calls=tuple(calls),
        modules=modules,
    )
    faults: list[Fault] = []
    for registration in registrations:
        matching: tuple[RuleTestAssociationFact, ...] = tuple(
            item
            for item in associations
            if item.rule_reference.module_name == registration.module_name
            and item.rule_reference.symbol_name == registration.function_name
        )
        count: int = sum(item.provable_case_count for item in matching)
        dynamic: bool = any(item.unknown_case_count for item in matching)
        if count >= minimum:
            continue
        detail: str = (
            "associated tests with dynamically determined case counts; the configured minimum "
            f"of {minimum} cannot be statically proven"
            if dynamic
            else f"{count} statically declared test cases; at least {minimum} is required"
        )
        faults.append(
            ctx.fault_for(
                path=registration.source_path,
                line=registration.declaration_line,
                column=registration.declaration_column,
                message=f"custom rule {registration.rule.code} has {detail}",
            )
        )
    return faults


def _module_name(*, path: Path, import_root: Path) -> str:
    parts: tuple[str, ...] = path.relative_to(import_root).with_suffix("").parts
    if parts and parts[-1] == INIT_MODULE_NAME:
        parts = parts[:-1]
    return ".".join(parts)
