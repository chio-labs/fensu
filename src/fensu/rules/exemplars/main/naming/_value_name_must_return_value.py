"""Public custom equivalent of native value-producing naming policy."""

import ast
from fnmatch import fnmatchcase

from fensu import ContractBehavior, Family, Fault, ReturnAnnotationCategory, RuleContext, rule


@rule(
    code="XCN003",
    family=Family.CUSTOM,
    slug="value-name-must-return-value-equivalent",
    message="value-producing names must not declare a no-value result",
    remediation=(
        "Return the queried or converted value, or rename the function to describe its side "
        "effect, such as initialize_cache or export_json."
    ),
)
def value_name_must_return_value_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFN003 entirely through the public custom-rule API."""

    del module
    patterns: tuple[str, ...] = tuple(
        pattern
        for pattern, behavior in ctx.contracts().items()
        if behavior == ContractBehavior.RETURNS_VALUE
    )
    faults: list[Fault] = []
    for fact in ctx.facts.function_contracts():
        if fact.return_annotation_category != ReturnAnnotationCategory.NONE:
            continue
        if not any(fnmatchcase(fact.function_name, pattern) for pattern in patterns):
            continue
        faults.append(
            ctx.fault_at(
                location=fact.location,
                message=(
                    f"function '{fact.function_name}' uses a value-producing name but declares "
                    f"'{fact.return_annotation}'"
                ),
                remediation=_remediation(fact.function_name),
            )
        )
    return faults


def _remediation(function_name: str) -> str:
    if function_name.startswith("get_"):
        return (
            "Return the queried value (including an optional value when absence is valid), or "
            "rename a command for its action, such as initialize_cache, populate_cache, or "
            "update_cache."
        )
    return (
        "Return the converted representation, or rename a side-effecting operation to describe "
        "its destination, such as write_json or export_json."
    )
