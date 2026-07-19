"""Public custom equivalents of native basic pytest-function policies."""

import ast
import re

from strata import Family, Fault, RuleContext, ScopeName, rule
from strata.rules.exemplars.types import ExemplarTestPathName, ExemplarTestSymbol


@rule(
    code="XCT302",
    family=Family.CUSTOM,
    slug="test-function-name-equivalent",
    message="test functions must use test_given_<state>_when_<action>_then_<outcome>",
    remediation=(
        "Rename the test so its precondition, action, and expected behavior are explicit."
    ),
)
def test_function_name_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT302 through public pytest-function facts."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    pattern: re.Pattern[str] = re.compile(r"^test_given_.+_when_.+_then_.+$")
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if not pattern.match(fact.name)
    ]


@rule(
    code="XCT401",
    family=Family.CUSTOM,
    slug="dataclass-parametrize-equivalent",
    message="tests must use dataclass-backed pytest parameterization",
    remediation="Add @pytest.mark.parametrize with local test_case dataclass instances.",
)
def _dataclass_parametrize_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is None
    ]


@rule(
    code="XCT402",
    family=Family.CUSTOM,
    slug="accepts-test-case-equivalent",
    message="parametrized tests must accept a test_case argument",
    remediation="Name the parameter test_case and read inputs and expectations from that object.",
)
def _accepts_test_case_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None and ExemplarTestSymbol.TEST_CASE not in fact.parameter_names
    ]
