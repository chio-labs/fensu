"""Public custom equivalent of tooling package layout policy."""

import ast
from pathlib import Path

from fensu import Fault, RuleContext, ScopeName
from fensu.rules.catalog.main._get_rule_constraint import get_rule_constraint
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule
from fensu.rules.exemplars._helpers.package_anchors import is_package_anchor
from fensu.rules.exemplars.types import ExemplarTestLimit, ExemplarTestPathName


@equivalent_rule(
    core_code="FFR705",
    code="XCR705",
    slug="tooling-package-layout-equivalent",
)
def tooling_package_layout_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR705 through public position and package observations."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    role_directories: tuple[str, ...] = get_rule_constraint(
        code="FFR705", name="allowed_tooling_role_directories"
    )
    role_files: tuple[str, ...] = get_rule_constraint(
        code="FFR705", name="allowed_tooling_role_files"
    )
    minimum_parts: int = int(ExemplarTestLimit.MINIMUM_PATH_PARTS)
    if ctx.scope() is not ScopeName.TOOLING or len(parts) < minimum_parts:
        return []
    if len(parts) == minimum_parts:
        if parts[-1] == ExemplarTestPathName.INIT or parts[-1] in role_files:
            return []
        return [
            ctx.path_fault(message="tool packages may contain only role files and role directories")
        ]
    role_name: str = parts[1]
    if role_name in role_directories:
        return []
    package_dir: Path = ctx.scope_root().joinpath(*parts[:2])
    if not is_package_anchor(ctx=ctx, package_dir=package_dir):
        return []
    return [ctx.path_fault(message=f"tool package child '{role_name}/' is not an approved role")]
