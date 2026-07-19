"""Public custom equivalent of native test absolute-import policy."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule


@rule(
    code="XCT102",
    family=Family.CUSTOM,
    slug="test-absolute-imports-equivalent",
    message="tests must use absolute imports",
    remediation="Replace the relative import with the full tests or application package path.",
)
def test_absolute_imports_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT102 through public scope and reference facts."""

    del module
    if ctx.scope() is not ScopeName.TEST:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.references().imports
        if fact.from_import and fact.relative_level > 0
    ]
