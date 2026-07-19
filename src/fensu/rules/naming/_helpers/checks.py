"""Rule check functions for the naming family."""

from __future__ import annotations

import ast
from fnmatch import fnmatchcase

from fensu.analysis.models import FunctionContractFact
from fensu.analysis.types import ReturnAnnotationCategory
from fensu.config.exceptions import ConfigError
from fensu.config.types import ContractBehavior
from fensu.rules.authoring.models import Fault
from fensu.rules.authoring.types import RuleContext

_bool_categories: frozenset[ReturnAnnotationCategory] = frozenset(
    {
        ReturnAnnotationCategory.BOOL,
        ReturnAnnotationCategory.TYPE_GUARD,
        ReturnAnnotationCategory.TYPE_IS,
    }
)
_iterator_categories: frozenset[ReturnAnnotationCategory] = frozenset(
    {
        ReturnAnnotationCategory.ITERATOR,
        ReturnAnnotationCategory.GENERATOR,
        ReturnAnnotationCategory.ASYNC_ITERATOR,
        ReturnAnnotationCategory.ASYNC_GENERATOR,
    }
)


def validator_must_not_return(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag meaningful returns from functions under no-return name contracts."""

    del module
    faults: list[Fault] = []
    for fact, behaviors in _matched_contracts(ctx):
        if ContractBehavior.NO_RETURN in behaviors and fact.meaningful_return_location is not None:
            faults.append(
                ctx.fault_at(
                    location=fact.meaningful_return_location,
                    message=(
                        f"function '{fact.function_name}' uses a no-return name but returns "
                        "a meaningful value"
                    ),
                    remediation=(
                        "Remove the meaningful return and raise on invalid input, or rename the "
                        "value-producing function as a query such as is_valid or "
                        "get_validation_result."
                    ),
                )
            )
    return faults


def predicate_must_return_bool(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag predicate names whose declared result is not an ordinary boolean."""

    del module
    faults: list[Fault] = []
    for fact, behaviors in _matched_contracts(ctx):
        category: ReturnAnnotationCategory = ReturnAnnotationCategory(
            fact.return_annotation_category
        )
        if (
            ContractBehavior.RETURNS_BOOL in behaviors
            and category != ReturnAnnotationCategory.MISSING
            and category not in _bool_categories
        ):
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message=(
                        f"function '{fact.function_name}' uses a predicate name but declares "
                        f"'{fact.return_annotation}'"
                    ),
                    remediation=_predicate_remediation(fact.function_name),
                )
            )
    return faults


def value_name_must_return_value(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag value-producing names that explicitly declare no result."""

    del module
    faults: list[Fault] = []
    for fact, behaviors in _matched_contracts(ctx):
        if (
            ContractBehavior.RETURNS_VALUE in behaviors
            and ReturnAnnotationCategory(fact.return_annotation_category)
            == ReturnAnnotationCategory.NONE
        ):
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message=(
                        f"function '{fact.function_name}' uses a value-producing name but "
                        f"declares '{fact.return_annotation}'"
                    ),
                    remediation=_value_remediation(fact.function_name),
                )
            )
    return faults


def iterator_name_must_produce_iterator(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag iterator names not proven by owned yield or a declared iterator result."""

    del module
    faults: list[Fault] = []
    for fact, behaviors in _matched_contracts(ctx):
        category: ReturnAnnotationCategory = ReturnAnnotationCategory(
            fact.return_annotation_category
        )
        if (
            ContractBehavior.RETURNS_ITERATOR in behaviors
            and not fact.contains_yield
            and category != ReturnAnnotationCategory.MISSING
            and category not in _iterator_categories
        ):
            suffix: str = fact.function_name.removeprefix("iter_")
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message=(
                        f"function '{fact.function_name}' uses an iterator name but declares "
                        f"'{fact.return_annotation}'"
                    ),
                    remediation=(
                        "Return an iterator or generator, or rename an eager collection function "
                        f"with a name such as collect_{suffix}."
                    ),
                )
            )
    return faults


def _matched_contracts(
    ctx: RuleContext,
) -> tuple[tuple[FunctionContractFact, frozenset[ContractBehavior]], ...]:
    return ctx._memoize(key="naming.matched-contracts", operation=lambda: _match_contracts(ctx))


def _match_contracts(
    ctx: RuleContext,
) -> tuple[tuple[FunctionContractFact, frozenset[ContractBehavior]], ...]:
    contracts: tuple[tuple[str, ContractBehavior], ...] = tuple(
        (pattern, ContractBehavior(behavior)) for pattern, behavior in ctx.contracts().items()
    )
    matched: list[tuple[FunctionContractFact, frozenset[ContractBehavior]]] = []
    for fact in ctx.facts.function_contracts():
        pattern_behaviors: tuple[tuple[str, ContractBehavior], ...] = tuple(
            sorted(
                (
                    (pattern, behavior)
                    for pattern, behavior in contracts
                    if fnmatchcase(fact.function_name, pattern)
                ),
                key=lambda item: item[0],
            )
        )
        behaviors: frozenset[ContractBehavior] = frozenset(
            behavior for _, behavior in pattern_behaviors
        )
        if len(behaviors) > 1:
            details: str = ", ".join(
                f"'{pattern}' ({behavior.value})" for pattern, behavior in pattern_behaviors
            )
            relative_path: str = ctx.path.relative_to(ctx.repo_root).as_posix()
            raise ConfigError(
                f"Conflicting contracts for function '{fact.function_name}' at "
                f"{relative_path}: {details}."
            )
        if behaviors:
            matched.append((fact, behaviors))
    return tuple(matched)


def _predicate_remediation(function_name: str) -> str:
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


def _value_remediation(function_name: str) -> str:
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
