"""Public custom equivalent of Python module-execution reachability."""

from fensu import ExecutionOwner, Family, Fault, Project, RuleContext, rule
from fensu.rules.exemplars._helpers.reachability import unreachable_symbols


@rule(
    code="XCL108",
    family=Family.CUSTOM,
    slug="unreachable-module-equivalent",
    message="module is unreachable from production roots",
    execution_owner=ExecutionOwner.PROJECT,
)
def unreachable_module_equivalent(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Traverse execution nodes without implicitly retaining all module declarations."""

    del project
    return unreachable_symbols(ctx=ctx, modules_only=True)
