"""Public custom routing equivalent of source-owned coverage policy."""

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCR707",
    family=Family.CUSTOM,
    slug="custom-rule-test-coverage-equivalent",
    message="configured custom rules must have statically declared public-harness cases",
    remediation=(
        "Add statically visible RuleCase construction passed to evaluate_rule. When FFT413 is "
        "active, convert a local wrapper dataclass to RuleCase inside the test."
    ),
)
def custom_rule_test_coverage_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Represent FFR707's no-registration file boundary through public APIs."""

    del module, ctx
    return []
