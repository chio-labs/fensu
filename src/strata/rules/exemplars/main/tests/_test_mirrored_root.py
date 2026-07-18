"""Public custom equivalent of configured test mirror roots."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule
from strata.rules.exemplars._helpers.test_layout import layout_issue
from strata.rules.exemplars.types import ExemplarTestPathName


@rule(
    code="XCT003",
    family=Family.CUSTOM,
    slug="test-mirrored-root-equivalent",
    message="test directories must mirror a configured runtime or tooling root",
    remediation="Mirror the complete configured source or tooling path beneath the test scope.",
)
def test_mirrored_root_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT003 through public configured-root facts."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in (
        ExemplarTestPathName.INIT,
        ExemplarTestPathName.CONFTEST,
    ):
        return []
    code: str = "SFT003"
    issue: tuple[str, str] | None = layout_issue(ctx=ctx)
    return [] if issue is None or issue[0] != code else [ctx.path_fault(message=issue[1])]
