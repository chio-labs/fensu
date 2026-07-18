"""Public custom equivalents of runtime test mirror policies."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule
from strata.rules.exemplars._helpers.test_layout import layout_issue
from strata.rules.exemplars.types import ExemplarTestPathName


def _faults(*, ctx: RuleContext, code: str) -> list[Fault]:
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in (
        ExemplarTestPathName.INIT,
        ExemplarTestPathName.CONFTEST,
    ):
        return []
    issue: tuple[str, str] | None = layout_issue(ctx=ctx)
    return [] if issue is None or issue[0] != code else [ctx.path_fault(message=issue[1])]


@rule(
    code="XCT004",
    family=Family.CUSTOM,
    slug="src-mirror-depth-equivalent",
    message="runtime tests must include an area beneath the configured source root",
    remediation="Move the test beneath the package and source area it exercises.",
)
def src_mirror_depth_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT004 through public configured-root facts."""

    del module
    return _faults(ctx=ctx, code="SFT004")


@rule(
    code="XCT005",
    family=Family.CUSTOM,
    slug="src-package-exists-equivalent",
    message="runtime tests must mirror a configured source package",
    remediation="Correct the mirrored package name or move the test to the package it exercises.",
)
def _src_package_exists_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    return _faults(ctx=ctx, code="SFT005")
