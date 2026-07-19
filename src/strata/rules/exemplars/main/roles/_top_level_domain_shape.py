"""Public custom equivalent of top-level domain shape policy."""

import ast

from strata import ExecutionOwner, Family, Fault, RuleContext, rule
from strata.rules.exemplars._helpers.non_file_rules import top_level_domain_shape_impl


@rule(
    code="XCR306",
    family=Family.CUSTOM,
    slug="top-level-domain-shape-equivalent",
    message="top-level domains must be either role leaves or subdomain branches",
    execution_owner=ExecutionOwner.DOMAIN,
)
def top_level_domain_shape_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFR306 through public project and position APIs."""

    return top_level_domain_shape_impl(module=module, ctx=ctx)
