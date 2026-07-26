"""Public custom equivalent of main package layout policy."""

import ast

from fensu import ExecutionOwner, Fault, RuleContext, Threshold
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule
from fensu.rules.exemplars._helpers.non_file_rules import package_layout_impl


@equivalent_rule(
    core_code="FFR302",
    code="XCR302",
    slug="main-package-layout-equivalent",
    execution_owner=ExecutionOwner.PACKAGE,
)
def main_package_layout_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR302 through public project and threshold APIs."""

    return package_layout_impl(
        module=module, ctx=ctx, role="main", threshold=Threshold.MAX_MAIN_CONTAINER_MODULES
    )
