"""Public custom equivalent of helpers package layout policy."""

import ast

from fensu import ExecutionOwner, Family, Fault, RuleContext, Threshold, rule
from fensu.rules.exemplars._helpers.non_file_rules import package_layout_impl


@rule(
    code="XCR301",
    family=Family.CUSTOM,
    slug="helpers-package-layout-equivalent",
    message="_helpers/ packages must use bounded flat-or-grouped containers",
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
