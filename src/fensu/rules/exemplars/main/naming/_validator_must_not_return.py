"""Public custom equivalent of native no-return naming policy."""

import ast
from fnmatch import fnmatchcase

from fensu import ContractBehavior, Family, Fault, RuleContext, rule


@rule(
    code="XCN001",
    family=Family.CUSTOM,
    slug="validator-must-not-return-equivalent",
    message="functions under no-return naming contracts must not return values",
    remediation=(
        "Remove the meaningful return and raise on invalid input, or rename a value-producing "
        "function as a query such as is_valid or get_validation_result."
    ),
)
def validator_must_not_return_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFN001 entirely through the public custom-rule API."""

    del module
    patterns: tuple[str, ...] = tuple(
        pattern
        for pattern, behavior in ctx.contracts().items()
        if behavior == ContractBehavior.NO_RETURN
    )
    faults: list[Fault] = []
    for fact in ctx.facts.function_contracts():
        if fact.meaningful_return_location is None or not any(
            fnmatchcase(fact.function_name, pattern) for pattern in patterns
        ):
            continue
        faults.append(
            ctx.fault_at(
                location=fact.meaningful_return_location,
                message=(
                    f"function '{fact.function_name}' uses a no-return name but returns a "
                    "meaningful value"
                ),
                remediation=(
                    "Remove the meaningful return and raise on invalid input, or rename the "
                    "value-producing function as a query such as is_valid or "
                    "get_validation_result."
                ),
            )
        )
    return faults
