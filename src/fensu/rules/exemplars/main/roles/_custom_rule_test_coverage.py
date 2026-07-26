"""Public custom routing equivalent of source-owned coverage policy."""

import ast

from fensu import Fault, RuleContext
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule


@equivalent_rule(
    core_code="FFR707",
    code="XCR707",
    slug="custom-rule-test-coverage-equivalent",
)
def custom_rule_test_coverage_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Represent FFR707's no-registration file boundary through public APIs."""

    del module, ctx
    return []
