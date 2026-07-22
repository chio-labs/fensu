"""Public custom equivalent of local test-types file policy."""

import ast
from pathlib import Path

from fensu import Family, Fault, RuleContext, ScopeName, rule
from fensu.rules.exemplars.types import ExemplarTestPathName


@rule(
    code="XCT204",
    family=Family.CUSTOM,
    slug="local-test-types-file-equivalent",
    message="test directories must provide a local _test_types.py",
    remediation=(
        "Create _test_types.py beside the test. Custom-rule tests should define a local wrapper "
        "dataclass there rather than parametrizing directly with RuleCase."
    ),
)
def local_test_types_file_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT204 through the public file observation API."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    path: Path = ctx.path.parent / ExemplarTestPathName.TEST_TYPES
    return [] if ctx.project.is_file(requester=ctx.path, path=path) else [ctx.path_fault()]
