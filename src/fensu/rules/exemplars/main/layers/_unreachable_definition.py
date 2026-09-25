"""Public custom equivalent of module-level Python definition reachability."""

from fensu import ExecutionOwner, Family, Fault, Project, RuleContext, rule
from fensu.rules.exemplars._helpers.reachability import unreachable_symbols


@rule(
    code="XCL106",
    family=Family.CUSTOM,
    slug="unreachable-definition-equivalent",
    message="definition is unreachable from production roots",
    execution_owner=ExecutionOwner.PROJECT,
)
def unreachable_definition_equivalent(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Express FFL106 using public declarations, roots, and resolved reference edges."""

    del project
    return unreachable_symbols(ctx=ctx, modules_only=False)
