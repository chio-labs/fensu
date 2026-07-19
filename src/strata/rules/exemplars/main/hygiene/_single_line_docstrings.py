"""Public custom equivalent of native multiline-docstring policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCH001",
    family=Family.CUSTOM,
    slug="single-line-docstrings-equivalent",
    message="docstrings must be a single line; move extended explanation into docs or tests",
    remediation=(
        "Keep one concise summary line and move extended rationale into documentation or tests."
    ),
)
def single_line_docstrings_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFH001 through public hygiene facts."""

    del module
    return [ctx.fault_at(location=item) for item in ctx.facts.hygiene().multiline_docstrings]
