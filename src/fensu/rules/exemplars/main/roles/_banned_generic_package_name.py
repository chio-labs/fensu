"""Public custom equivalent of generic package ownership policy."""

import ast
from pathlib import Path

from fensu import Family, Fault, RuleContext, ScopeName, rule
from fensu.rules.exemplars._helpers.package_anchors import is_package_anchor
from fensu.rules.exemplars.types import ExemplarBannedPackageName


@rule(
    code="XCR204",
    family=Family.CUSTOM,
    slug="banned-generic-package-name-equivalent",
    message="runtime package directories must identify an owner",
    remediation="Rename the package after the business domain or technical capability it owns.",
)
def banned_generic_package_name_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR204 through public path and project APIs."""

    del module
    if ctx.scope() is ScopeName.TOOLING:
        return []
    faults: list[Fault] = []
    parts: tuple[str, ...] = ctx.relative_parts()
    for index, name in enumerate(parts[:-1]):
        package_dir: Path = ctx.scope_root().joinpath(*parts[: index + 1])
        if name in set(ExemplarBannedPackageName) and is_package_anchor(
            ctx=ctx, package_dir=package_dir
        ):
            faults.append(
                ctx.path_fault(
                    message=(
                        f"{name}/ does not identify an owner; name the business or technical "
                        "capability"
                    )
                )
            )
    return faults
