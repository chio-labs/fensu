"""Public custom equivalent of native private-definition ordering policy."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule


@rule(
    code="XCR503",
    family=Family.CUSTOM,
    slug="private-definition-ordering-equivalent",
    message="private constants and dataclasses must appear before top-level functions",
    remediation=(
        "Move private module declarations above the first function so readers see module state "
        "before behavior."
    ),
)
def private_definition_ordering_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR503 through public scope and declaration facts."""

    del module
    if ctx.scope() is ScopeName.TEST:
        return []
    faults: list[Fault] = []
    saw_function: bool = False
    for fact in ctx.facts.module_declarations().statements:
        if fact.function_name is not None:
            saw_function = True
            continue
        if not saw_function:
            continue
        if fact.class_name is not None and fact.class_name.startswith("_") and fact.dataclass_class:
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message="private dataclasses must appear before top-level functions",
                )
            )
        elif any(name.startswith("_") for name in fact.assignment_target_names):
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message="private constants must appear before top-level functions",
                )
            )
    return faults
