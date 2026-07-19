"""Public custom equivalent of native helper-private class policy."""

import ast

from strata import AttributeReferenceFact, Family, Fault, ImportFact, RuleContext, ScopeName, rule


@rule(
    code="XCL110",
    family=Family.CUSTOM,
    slug="no-cross-file-use-of-helper-private-class-equivalent",
    message="helper-private classes are file-local details; move shared classes to classes/",
    remediation="If another module needs this class, move it to the owning classes/ package.",
)
def no_cross_file_helper_private_classes_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express SFL110 through public scope and ordered reference facts."""

    del module
    if ctx.scope() is ScopeName.TEST:
        return []
    faults: list[Fault] = []
    helper_module_aliases: set[str] = set()
    for event in ctx.facts.references().events:
        if isinstance(event, ImportFact):
            if event.from_import and any(_is_helpers_part(part) for part in event.module_parts):
                for alias in event.aliases:
                    if _is_private_class_name(alias.imported_name):
                        faults.append(ctx.fault_at(location=event.location))
                    else:
                        helper_module_aliases.add(alias.bound_name)
            elif not event.from_import:
                for alias in event.aliases:
                    if not any(_is_helpers_part(part) for part in alias.imported_parts):
                        continue
                    imported_name: str = alias.imported_parts[-1]
                    if _is_private_class_name(imported_name):
                        faults.append(ctx.fault_at(location=event.location))
                    else:
                        helper_module_aliases.add(alias.bound_name)
        elif (
            isinstance(event, AttributeReferenceFact)
            and _is_private_class_name(event.attribute_name)
            and event.base_name in helper_module_aliases
        ):
            faults.append(ctx.fault_at(location=event.location))
    return faults


def _is_private_class_name(name: str) -> bool:
    return len(name) > 1 and name.startswith("_") and name[1].isupper()


def _is_helpers_part(part: str) -> bool:
    return part.startswith("_helpers") and not part.removeprefix("_helpers")
