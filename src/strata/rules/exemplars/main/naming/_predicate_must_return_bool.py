"""Public custom equivalent of native predicate naming policy."""

import ast
from fnmatch import fnmatchcase

from strata import ContractBehavior, Family, Fault, ReturnAnnotationCategory, RuleContext, rule


@rule(
    code="XCN002",
    family=Family.CUSTOM,
    slug="predicate-must-return-bool-equivalent",
    message="predicate names must declare an ordinary boolean result",
    remediation=(
        "Return bool (or TypeGuard/TypeIs), or rename the function to describe the value it "
        "returns, such as read_status or current_status."
    ),
)
def predicate_must_return_bool_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFN002 entirely through the public custom-rule API."""

    del module
    patterns: tuple[str, ...] = tuple(
        pattern
        for pattern, behavior in ctx.contracts().items()
        if behavior == ContractBehavior.RETURNS_BOOL
    )
    accepted: frozenset[ReturnAnnotationCategory] = frozenset(
        {
            ReturnAnnotationCategory.BOOL,
            ReturnAnnotationCategory.TYPE_GUARD,
            ReturnAnnotationCategory.TYPE_IS,
        }
    )
    faults: list[Fault] = []
    for fact in ctx.facts.function_contracts():
        if fact.return_annotation_category == ReturnAnnotationCategory.MISSING:
            continue
        if fact.return_annotation_category in accepted:
            continue
        if not any(fnmatchcase(fact.function_name, pattern) for pattern in patterns):
            continue
        faults.append(
            ctx.fault_at(
                location=fact.location,
                message=(
                    f"function '{fact.function_name}' uses a predicate name but declares "
                    f"'{fact.return_annotation}'"
                ),
                remediation=_remediation(fact.function_name),
            )
        )
    return faults


def _remediation(function_name: str) -> str:
    if function_name.startswith("has_"):
        rename: str = f"count_{function_name.removeprefix('has_')}"
    elif function_name.startswith("can_"):
        suffix: str = function_name.removeprefix("can_")
        rename = f"explain_{suffix} or {suffix}_reason"
    elif function_name.startswith("supports_"):
        suffix = function_name.removeprefix("supports_")
        rename = f"supported_{suffix} or capabilities"
    else:
        suffix = function_name.removeprefix("is_")
        rename = f"read_{suffix} or current_{suffix}"
    return (
        "Return bool (or TypeGuard/TypeIs), or rename the function to describe the value it "
        f"returns, such as {rename}."
    )
