"""Public custom equivalent of leaf main boundary policy."""

import ast

from fensu import ExecutionOwner, Fault, RuleContext
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule
from fensu.rules.exemplars._helpers.non_file_rules import leaf_main_boundary_impl


@equivalent_rule(
    core_code="FFR309",
    code="XCR309",
    slug="leaf-main-boundary-equivalent",
    execution_owner=ExecutionOwner.LEAF,
)
def leaf_main_boundary_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR309 through public project and position APIs."""

    return leaf_main_boundary_impl(module=module, ctx=ctx)
