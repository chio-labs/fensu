"""Public custom equivalent of native iterator naming policy."""

import ast
from fnmatch import fnmatchcase

from strata import ContractBehavior, Family, Fault, ReturnAnnotationCategory, RuleContext, rule


@rule(
    code="XCN004",
    family=Family.CUSTOM,
    slug="iterator-name-must-produce-iterator-equivalent",
    message="iterator names must produce an iterator or generator",
    remediation=(
        "Return an iterator or generator, or rename an eager collection function with a name "
        "such as collect_items."
    ),
)
def iterator_name_must_produce_iterator_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express SFN004 entirely through the public custom-rule API."""

    del module
    patterns: tuple[str, ...] = tuple(
        pattern
        for pattern, behavior in ctx.contracts().items()
        if behavior == ContractBehavior.RETURNS_ITERATOR
    )
    accepted: frozenset[ReturnAnnotationCategory] = frozenset(
        {
            ReturnAnnotationCategory.ITERATOR,
            ReturnAnnotationCategory.GENERATOR,
            ReturnAnnotationCategory.ASYNC_ITERATOR,
            ReturnAnnotationCategory.ASYNC_GENERATOR,
        }
    )
    faults: list[Fault] = []
    for fact in ctx.facts.function_contracts():
        if fact.contains_yield:
            continue
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
                    f"function '{fact.function_name}' uses an iterator name but declares "
                    f"'{fact.return_annotation}'"
                ),
                remediation=(
                    "Return an iterator or generator, or rename an eager collection function "
                    "with a name such as "
                    f"collect_{fact.function_name.removeprefix('iter_')}."
                ),
            )
        )
    return faults
