"""Public custom equivalent of reasoned-root staleness detection."""

from fensu import ExecutionOwner, Family, Fault, Project, RuleContext, rule
from fensu.rules.exemplars._helpers.reachability import stale_roots


@rule(
    code="XCL107",
    family=Family.CUSTOM,
    slug="stale-dead-code-root-equivalent",
    message="configured root matches no existing production declaration",
    execution_owner=ExecutionOwner.PROJECT,
)
def stale_dead_code_root_equivalent(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Match configured roots against declarations before considering reachability."""

    del project
    return stale_roots(ctx=ctx)
