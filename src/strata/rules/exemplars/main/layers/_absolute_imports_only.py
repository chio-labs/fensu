"""Public custom equivalent of native absolute-import policy."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule


@rule(
    code="XCL001",
    family=Family.CUSTOM,
    slug="absolute-imports-only-equivalent",
    message="use absolute imports; relative imports hide package boundaries",
    remediation="Replace relative imports with an absolute import path.",
)
def absolute_imports_only_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFL001 through public scope and reference facts."""

    del module
    if ctx.scope() is ScopeName.TEST:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.references().imports
        if fact.from_import and fact.relative_level > 0
    ]
