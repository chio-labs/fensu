"""Public custom equivalent of helpers package layout policy."""

import ast

from fensu import ExecutionOwner, Fault, RuleContext, Threshold
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule
from fensu.rules.exemplars._helpers.non_file_rules import package_layout_impl


@equivalent_rule(
    core_code="FFR301",
    code="XCR301",
    slug="helpers-package-layout-equivalent",
    execution_owner=ExecutionOwner.PACKAGE,
)
def helpers_package_layout_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR301 through public project and threshold APIs."""

    return package_layout_impl(
        module=module,
        ctx=ctx,
        role="_helpers",
        threshold=Threshold.MAX_HELPERS_CONTAINER_MODULES,
    )
