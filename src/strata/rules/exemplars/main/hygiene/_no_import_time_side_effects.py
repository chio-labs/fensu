"""Public custom equivalent of native import-time-call policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCH009",
    family=Family.CUSTOM,
    slug="no-import-time-side-effects-equivalent",
    message="runtime and tooling modules must not execute standalone calls during import",
    remediation="Move the operation into an explicit function or assign a pure constructor result.",
)
def no_import_time_side_effects_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFH009 through public module-declaration facts."""

    del module
    return [
        ctx.fault_at(location=item)
        for item in ctx.facts.module_declarations().import_time_call_locations
    ]
