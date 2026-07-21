"""Naming contract rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.naming.types import NamingCode


def contract_rules() -> tuple[RuleSpec, ...]:
    """Build naming contract rules."""

    return (
        RuleSpec(
            code=NamingCode.VALIDATOR_MUST_NOT_RETURN,
            family=Family.NAMING,
            slug="validator-must-not-return",
            message="functions under no-return naming contracts must not return values",
            remediation=(
                "Remove the meaningful return and raise on invalid input, or rename a "
                "value-producing function as a query such as is_valid or get_validation_result."
            ),
        ),
        RuleSpec(
            code=NamingCode.PREDICATE_MUST_RETURN_BOOL,
            family=Family.NAMING,
            slug="predicate-must-return-bool",
            message="predicate names must declare an ordinary boolean result",
            remediation=(
                "Return bool (or TypeGuard/TypeIs), or rename the function to describe the value "
                "it returns, such as read_status or current_status."
            ),
        ),
        RuleSpec(
            code=NamingCode.VALUE_NAME_MUST_RETURN_VALUE,
            family=Family.NAMING,
            slug="value-name-must-return-value",
            message="value-producing names must not declare a no-value result",
            remediation=(
                "Return the queried or converted value, or rename the function to describe its "
                "side effect, such as initialize_cache or export_json."
            ),
        ),
        RuleSpec(
            code=NamingCode.ITERATOR_NAME_MUST_PRODUCE_ITERATOR,
            family=Family.NAMING,
            slug="iterator-name-must-produce-iterator",
            message="iterator names must produce an iterator or generator",
            remediation=(
                "Return an iterator or generator, or rename an eager collection function with a "
                "name such as collect_items."
            ),
        ),
    )
