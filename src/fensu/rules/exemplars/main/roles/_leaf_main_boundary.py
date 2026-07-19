"""Public custom equivalent of leaf main boundary policy."""

import ast

from fensu import ExecutionOwner, Family, Fault, RuleContext, rule
from fensu.rules.exemplars._helpers.non_file_rules import leaf_main_boundary_impl


@rule(
    code="XCR309",
    family=Family.CUSTOM,
    slug="leaf-main-boundary-equivalent",
    message="leaf runtime domains and subdomains must expose meaningful behavior through main/",
    execution_owner=ExecutionOwner.LEAF,
)
def leaf_main_boundary_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR309 through public project and position APIs."""

    return leaf_main_boundary_impl(module=module, ctx=ctx)
