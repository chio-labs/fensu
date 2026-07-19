"""Public custom equivalents of basic test layout policies."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule
from fensu.rules.exemplars._helpers.test_layout import layout_issue
from fensu.rules.exemplars.types import ExemplarTestPathName


def _faults(*, ctx: RuleContext, code: str) -> list[Fault]:
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in (
        ExemplarTestPathName.INIT,
        ExemplarTestPathName.CONFTEST,
    ):
        return []
    issue: tuple[str, str] | None = layout_issue(ctx=ctx)
    return [] if issue is None or issue[0] != code else [ctx.path_fault(message=issue[1])]


@rule(
    code="XCT001",
    family=Family.CUSTOM,
    slug="test-layout-equivalent",
    message="tests must live under a configured test root and supported scope",
    remediation=(
        "Move the test beneath a configured test root and unit, integration, or e2e scope."
    ),
)
def test_layout_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT001 through public position and project APIs."""

    del module
    return _faults(ctx=ctx, code="FFT001")


@rule(
    code="XCT002",
    family=Family.CUSTOM,
    slug="test-scope-equivalent",
    message="test scope must be unit, integration, or e2e",
    remediation="Move the test under tests/unit, tests/integration, or tests/e2e.",
)
def _test_scope_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    return _faults(ctx=ctx, code="FFT002")
