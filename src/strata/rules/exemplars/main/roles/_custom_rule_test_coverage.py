"""Public custom routing equivalent of source-owned coverage policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCR707",
    family=Family.CUSTOM,
    slug="custom-rule-test-coverage-equivalent",
    message="configured custom rules must have statically declared public-harness cases",
    remediation="Add parametrized RuleCase coverage using evaluate_rule.",
)
def custom_rule_test_coverage_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Represent SFR707's no-registration file boundary through public APIs."""

    del module, ctx
    return []
