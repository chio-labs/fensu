"""Public custom equivalent of shared domain prefix policy."""

import ast

from fensu import ExecutionOwner, Fault, RuleContext
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule
from fensu.rules.exemplars._helpers.non_file_rules import shared_domain_prefix_impl


@equivalent_rule(
    core_code="FFR308",
    code="XCR308",
    slug="shared-domain-prefix-equivalent",
    execution_owner=ExecutionOwner.SCOPE,
)
def shared_domain_prefix_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR308 through public project and threshold APIs."""

    return shared_domain_prefix_impl(module=module, ctx=ctx)
