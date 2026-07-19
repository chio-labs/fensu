"""Public custom equivalents of native local test-type policies."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule
from fensu.rules.exemplars.types import ExemplarTestPathName, ExemplarTestSymbol


@rule(
    code="XCT201",
    family=Family.CUSTOM,
    slug="test-types-description-equivalent",
    message="test-case dataclasses must define a description field",
    remediation="Add description: str so parametrized cases explain the behavior they represent.",
)
def test_types_description_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT201 through public dataclass facts."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name != ExemplarTestPathName.TEST_TYPES:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.dataclasses()
        if ExemplarTestSymbol.DESCRIPTION not in fact.field_names
    ]


@rule(
    code="XCT202",
    family=Family.CUSTOM,
    slug="test-types-expected-field-equivalent",
    message="test-case dataclasses must define at least one expected_ field",
    remediation=(
        "Name expected outcomes with an expected_ prefix and assert against them in the test."
    ),
)
def _test_types_expected_field_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name != ExemplarTestPathName.TEST_TYPES:
        return []
    faults: list[Fault] = []
    for fact in ctx.facts.dataclasses():
        if not any(
            field_name.startswith(ExemplarTestSymbol.EXPECTED_PREFIX)
            for field_name in fact.field_names
        ):
            faults.append(ctx.fault_at(location=fact.location))
    return faults


@rule(
    code="XCT203",
    family=Family.CUSTOM,
    slug="local-test-types-import-equivalent",
    message="tests must import test-case types from their local _test_types.py",
    remediation=(
        "Move the dataclass beside the test and import it through the mirrored absolute path."
    ),
)
def _local_test_types_import_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    expected_module: str = ".".join(
        (ctx.path.parent / "_test_types.py").relative_to(ctx.repo_root).with_suffix("").parts
    )
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.references().imports
        if fact.top_level
        and fact.from_import
        and ".".join(fact.module_parts).endswith("._test_types")
        and ".".join(fact.module_parts) != expected_module
    ]
