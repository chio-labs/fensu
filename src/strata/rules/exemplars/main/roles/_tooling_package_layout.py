"""Public custom equivalent of tooling package layout policy."""

import ast
from pathlib import Path

from strata import Family, Fault, RuleContext, ScopeName, rule
from strata.rules.exemplars._helpers.package_anchors import is_package_anchor
from strata.rules.exemplars.types import (
    ExemplarTestLimit,
    ExemplarTestPathName,
    ExemplarToolingRoleFile,
    ExemplarToolingRoleName,
)


@rule(
    code="XCR705",
    family=Family.CUSTOM,
    slug="tooling-package-layout-equivalent",
    message="tool packages must organize implementation through explicit roles",
    remediation=(
        "Use main/, _helpers/, classes/, rules/, models.py, types.py, constants.py, or "
        "exceptions.py directly beneath scripts/<tool>/."
    ),
)
def tooling_package_layout_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFR705 through public position and package observations."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    minimum_parts: int = int(ExemplarTestLimit.MINIMUM_PATH_PARTS)
    if ctx.scope() is not ScopeName.TOOLING or len(parts) < minimum_parts:
        return []
    if len(parts) == minimum_parts:
        if parts[-1] == ExemplarTestPathName.INIT or parts[-1] in set(ExemplarToolingRoleFile):
            return []
        return [
            ctx.path_fault(message="tool packages may contain only role files and role directories")
        ]
    role_name: str = parts[1]
    if role_name in set(ExemplarToolingRoleName):
        return []
    package_dir: Path = ctx.scope_root().joinpath(*parts[:2])
    if not is_package_anchor(ctx=ctx, package_dir=package_dir):
        return []
    return [ctx.path_fault(message=f"tool package child '{role_name}/' is not an approved role")]
