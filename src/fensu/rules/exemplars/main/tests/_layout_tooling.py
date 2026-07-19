"""Public custom equivalents of tooling test mirror policies."""

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
    code="XCT007",
    family=Family.CUSTOM,
    slug="scripts-mirror-depth-equivalent",
    message="tooling tests must include an area beneath the configured tooling root",
    remediation="Move the test beneath the configured tooling area it exercises.",
)
def scripts_mirror_depth_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT007 through public configured-root facts."""

    del module
    return _faults(ctx=ctx, code="FFT007")


@rule(
    code="XCT008",
    family=Family.CUSTOM,
    slug="scripts-area-exists-equivalent",
    message="tooling tests must mirror an existing configured tooling area",
    remediation="Correct the mirrored area path so it matches the tooling location.",
)
def _scripts_area_exists_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    return _faults(ctx=ctx, code="FFT008")
