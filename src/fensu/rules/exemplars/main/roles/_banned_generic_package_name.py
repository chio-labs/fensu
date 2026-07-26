"""Public custom equivalent of generic package ownership policy."""

import ast
from pathlib import Path

from fensu import Fault, RuleContext, ScopeName
from fensu.rules.catalog.main._get_rule_constraint import get_rule_constraint
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule
from fensu.rules.exemplars._helpers.package_anchors import is_package_anchor


@equivalent_rule(
    core_code="FFR204",
    code="XCR204",
    slug="banned-generic-package-name-equivalent",
)
def banned_generic_package_name_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR204 through public path and project APIs."""

    del module
    if ctx.scope() is not ScopeName.ROOT:
        return []
    faults: list[Fault] = []
    parts: tuple[str, ...] = ctx.relative_parts()
    forbidden_names: tuple[str, ...] = get_rule_constraint(
        code="FFR204", name="forbidden_package_names"
    )
    for index, name in enumerate(parts[:-1]):
        package_dir: Path = ctx.scope_root().joinpath(*parts[: index + 1])
        if name in forbidden_names and is_package_anchor(ctx=ctx, package_dir=package_dir):
            faults.append(
                ctx.path_fault(
                    message=(
                        f"{name}/ does not identify an owner; name the business or technical "
                        "capability"
                    )
                )
            )
    return faults
