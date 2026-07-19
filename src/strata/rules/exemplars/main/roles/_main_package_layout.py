"""Public custom equivalent of main package layout policy."""

import ast

from strata import ExecutionOwner, Family, Fault, RuleContext, Threshold, rule
from strata.rules.exemplars._helpers.non_file_rules import package_layout_impl


@rule(
    code="XCR302",
    family=Family.CUSTOM,
    slug="main-package-layout-equivalent",
    message="main/ packages must use bounded flat-or-grouped orchestration containers",
    execution_owner=ExecutionOwner.PACKAGE,
)
def main_package_layout_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFR302 through public project and threshold APIs."""

    return package_layout_impl(
        module=module, ctx=ctx, role="main", threshold=Threshold.MAX_MAIN_CONTAINER_MODULES
    )
