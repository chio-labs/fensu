"""Public custom equivalents of native local test-module style policies."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule
from strata.rules.exemplars.types import ExemplarTestPathName


@rule(
    code="XCT101",
    family=Family.CUSTOM,
    slug="test-init-module-empty-equivalent",
    message="test package __init__.py files must be empty or docstring-only",
    remediation=(
        "Remove runtime declarations from __init__.py and import them from their owning module."
    ),
)
def test_init_module_empty_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT101 through public scope and test-module facts."""

    del module
    if (
        ctx.scope() is not ScopeName.TEST
        or ctx.path.name != ExemplarTestPathName.INIT
        or ctx.facts.test_module().empty_or_docstring_only
    ):
        return []
    return [ctx.path_fault(message="__init__.py must be empty or docstring-only")]


@rule(
    code="XCT103",
    family=Family.CUSTOM,
    slug="test-no-top-level-helpers-equivalent",
    message="test modules may contain only tests, imports, and declarations",
    remediation="Move reusable functions into the local helpers.py module.",
)
def _test_no_top_level_helpers_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.test_module().top_level_helper_locations
    ]


@rule(
    code="XCT105",
    family=Family.CUSTOM,
    slug="test-private-constant-order-equivalent",
    message="private test constants must appear before test functions",
    remediation=(
        "Move the private constant above the first test so module setup is visible before behavior."
    ),
)
def _test_private_constant_order_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.test_module().private_after_test_locations
    ]
