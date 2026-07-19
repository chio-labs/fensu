"""Public custom equivalents of native pytest-function expectation policies."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule
from fensu.rules.exemplars.types import ExemplarTestLimit, ExemplarTestPathName, ExemplarTestSymbol


@rule(
    code="XCT404",
    family=Family.CUSTOM,
    slug="expected-field-assertion-equivalent",
    message="tests must assert against an expected_ field from test_case",
    remediation=(
        "Store the expected outcome on test_case and reference it in a behavior assertion."
    ),
)
def expected_field_assertion_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT404 through public pytest-function facts."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None and not fact.references_expected_field
    ]


@rule(
    code="XCT405",
    family=Family.CUSTOM,
    slug="parametrize-arguments-equivalent",
    message="pytest parametrize decorators must define parameter names and values",
    remediation="Pass both the parameter-name string and the case sequence to parametrize.",
)
def _parametrize_arguments_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None
        and fact.parametrize.argument_count < int(ExemplarTestLimit.MINIMUM_PARAMETRIZE_ARGUMENTS)
    ]


@rule(
    code="XCT406",
    family=Family.CUSTOM,
    slug="parametrize-test-case-equivalent",
    message="pytest parametrize must expose cases through the test_case parameter",
    remediation='Use "test_case" as the parametrize parameter name.',
)
def _parametrize_test_case_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None
        and fact.parametrize.argument_count >= int(ExemplarTestLimit.MINIMUM_PARAMETRIZE_ARGUMENTS)
        and fact.parametrize.parameter_name != ExemplarTestSymbol.TEST_CASE
    ]
