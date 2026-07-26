"""Public custom equivalent of native standalone-comment policy."""

import ast

from fensu import Fault, RuleContext
from fensu.rules.catalog.main._get_rule_constraint import get_rule_constraint
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule


@equivalent_rule(
    core_code="FFH002",
    code="XCH002",
    slug="no-standalone-comments-equivalent",
)
def no_standalone_comments_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFH002 through public comment facts."""

    del module
    allowed_prefixes: tuple[str, ...] = get_rule_constraint(
        code="FFH002", name="allowed_standalone_comment_prefixes"
    )
    return [
        ctx.fault_for(path=fact.path, line=fact.line, column=fact.column)
        for fact in ctx.facts.comments()
        if not fact.text.startswith(allowed_prefixes)
    ]
