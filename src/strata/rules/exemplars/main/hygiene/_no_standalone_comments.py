"""Public custom equivalent of native standalone-comment policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCH002",
    family=Family.CUSTOM,
    slug="no-standalone-comments-equivalent",
    message="standalone comments are not allowed; prefer clear names or docs/tests",
    remediation=(
        "Replace the comment with clearer names or move lasting explanation into documentation "
        "or tests."
    ),
)
def no_standalone_comments_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFH002 through public comment facts."""

    del module
    return [
        ctx.fault_for(path=fact.path, line=fact.line, column=fact.column)
        for fact in ctx.facts.comments()
        if not fact.text.startswith(
            (
                "#!",
                "# -*-",
                "# coding:",
                "# noqa",
                "# type:",
                "# pyright:",
                "# pylint:",
                "# pragma:",
            )
        )
    ]
