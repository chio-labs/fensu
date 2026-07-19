"""Public custom equivalent of shared domain prefix policy."""

import ast

from fensu import ExecutionOwner, Family, Fault, RuleContext, rule
from fensu.rules.exemplars._helpers.non_file_rules import shared_domain_prefix_impl


@rule(
    code="XCR308",
    family=Family.CUSTOM,
    slug="shared-domain-prefix-equivalent",
    message="sibling domains must not encode one parent domain through a shared name prefix",
    execution_owner=ExecutionOwner.SCOPE,
)
def shared_domain_prefix_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR308 through public project and threshold APIs."""

    return shared_domain_prefix_impl(module=module, ctx=ctx)
