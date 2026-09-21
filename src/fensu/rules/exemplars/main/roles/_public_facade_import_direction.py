"""Public custom equivalent of public-facade import direction policy."""

import ast

from fensu import Fault, RuleContext
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule
from fensu.rules.exemplars._helpers.public_facades import public_facade_import_direction_impl


@equivalent_rule(
    core_code="FFR310",
    code="XCR310",
    slug="public-facade-import-direction-equivalent",
)
def public_facade_import_direction_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express FFR310 through public project and semantic-fact APIs."""

    return public_facade_import_direction_impl(module=module, ctx=ctx)
