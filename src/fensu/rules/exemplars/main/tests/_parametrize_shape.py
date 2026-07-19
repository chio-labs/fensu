"""Public custom equivalents of native pytest-parametrize shape policies."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule
from fensu.rules.exemplars.types import ExemplarTestLimit, ExemplarTestPathName


@rule(
    code="XCT407",
    family=Family.CUSTOM,
    slug="parametrize-ids-equivalent",
    message="pytest parametrize decorators must define readable case ids",
    remediation=(
        "Set ids to the case descriptions, normally with ids=lambda case: case.description."
    ),
)
def parametrize_ids_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT407 through public parametrize facts."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None
        and fact.parametrize.argument_count >= int(ExemplarTestLimit.MINIMUM_PARAMETRIZE_ARGUMENTS)
        and not fact.parametrize.ids_present
    ]


@rule(
    code="XCT408",
    family=Family.CUSTOM,
    slug="inline-parametrize-values-equivalent",
    message="pytest parametrize values must be a visible list, tuple, or local comprehension",
    remediation=(
        "Inline the case sequence in @pytest.mark.parametrize so its cases are visible beside "
        "the test."
    ),
)
def _inline_parametrize_values_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None
        and fact.parametrize.argument_count >= int(ExemplarTestLimit.MINIMUM_PARAMETRIZE_ARGUMENTS)
        and not fact.parametrize.values_is_sequence
        and not fact.parametrize.values_is_comprehension
    ]


@rule(
    code="XCT411",
    family=Family.CUSTOM,
    slug="nonempty-parametrize-values-equivalent",
    message="pytest parametrize case sequences must not be empty",
    remediation="Add at least one behavior case or remove the test until a real case exists.",
)
def _nonempty_parametrize_values_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None
        and fact.parametrize.argument_count >= int(ExemplarTestLimit.MINIMUM_PARAMETRIZE_ARGUMENTS)
        and fact.parametrize.values_is_sequence
        and fact.parametrize.values_empty
    ]
