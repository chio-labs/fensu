"""Public custom equivalent of main entry collision policy."""

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCR405",
    family=Family.CUSTOM,
    slug="main-entry-name-collision-equivalent",
    message="main/ cannot define a module and package with the same entry name",
    remediation=(
        "Choose either the flat entry module or the same-named package and remove the competing "
        "surface."
    ),
)
def main_entry_name_collision_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR405 through the public directory observation API."""

    del module
    if not ctx.is_entry_module() or not ctx.project.is_dir(
        requester=ctx.path, path=ctx.path.with_suffix("")
    ):
        return []
    return [ctx.path_fault(message="main entry name collides with package")]
