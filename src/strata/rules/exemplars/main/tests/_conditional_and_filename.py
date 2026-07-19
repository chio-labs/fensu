"""Public custom equivalents of native local conditional and filename policies."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule
from strata.rules.exemplars.types import ExemplarTestPathName


@rule(
    code="XCT104",
    family=Family.CUSTOM,
    slug="test-no-if-in-tests-equivalent",
    message="tests and local test helpers must not contain conditional control flow",
    remediation=(
        "Use parametrized cases when setup and assertions remain branch-free; otherwise split the "
        "behavior into separate test functions. Keep local test helpers deterministic with "
        "per-variant functions or dataclass-driven case data."
    ),
)
def test_no_if_in_tests_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT104 through public local control-flow facts."""

    del module
    if ctx.scope() is not ScopeName.TEST:
        return []
    if ctx.path.name in {ExemplarTestPathName.HELPERS, ExemplarTestPathName.TEST_HELPERS}:
        return [
            ctx.fault_at(location=location)
            for location in ctx.facts.top_level_definition_conditionals()
        ]
    if ctx.path.name in set(ExemplarTestPathName):
        return []
    faults: list[Fault] = []
    for fact in ctx.facts.test_functions():
        faults.extend(ctx.fault_at(location=location) for location in fact.conditional_locations)
    return faults


@rule(
    code="XCT301",
    family=Family.CUSTOM,
    slug="test-file-name-equivalent",
    message="test modules must use a test_ filename",
    remediation="Rename the module to test_<behavior>.py.",
)
def _test_file_name_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if (
        ctx.scope() is ScopeName.TEST
        and ctx.path.name not in set(ExemplarTestPathName)
        and not ctx.path.name.startswith("test_")
    ):
        return [ctx.path_fault()]
    return []
