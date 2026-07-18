"""Public custom equivalent of runtime test area existence."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule
from strata.rules.exemplars._helpers.test_layout import layout_issue
from strata.rules.exemplars.types import ExemplarTestPathName


@rule(
    code="XCT006",
    family=Family.CUSTOM,
    slug="src-area-exists-equivalent",
    message="runtime tests must mirror an existing source package area",
    remediation="Correct the mirrored area path so it matches the runtime module location.",
)
def src_area_exists_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT006 through public runtime-area observations."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in (
        ExemplarTestPathName.INIT,
        ExemplarTestPathName.CONFTEST,
    ):
        return []
    code: str = "SFT006"
    issue: tuple[str, str] | None = layout_issue(ctx=ctx)
    return [] if issue is None or issue[0] != code else [ctx.path_fault(message=issue[1])]
