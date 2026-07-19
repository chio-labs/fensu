"""Public custom equivalent of private main-entry import policy."""

import ast

from fensu import Family, Fault, RuleContext, rule
from fensu.rules.exemplars._helpers.import_ownership import (
    normalized_targets,
    ownership,
    target_module_exists,
)
from fensu.rules.exemplars.types import (
    ExemplarLayerPathName,
    ExemplarRoleName,
    ImportOwnership,
)


@rule(
    code="XCL104",
    family=Family.CUSTOM,
    slug="no-cross-domain-private-main-imports-equivalent",
    message="domain-private main entries may only be imported within their owning domain",
    remediation=(
        "Remove the leading underscore to publish the main entry, or route the caller through a "
        "public main entry owned by the target domain."
    ),
)
def no_cross_domain_private_main_imports_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express FFL104 through public import and project file observations."""

    del module
    current: ImportOwnership = ownership(
        parts=ctx.module_parts(), initializer=ctx.path.name == ExemplarLayerPathName.INIT
    )
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        bases: tuple[tuple[str, ...], ...] = normalized_targets(
            fact=fact,
            current_parts=ctx.module_parts(),
            initializer=ctx.path.name == ExemplarLayerPathName.INIT,
        )
        target_items: list[tuple[str, ...]] = list(bases)
        if fact.from_import:
            for base in bases:
                target_items.extend((*base, *alias.imported_parts) for alias in fact.aliases)
        targets: tuple[tuple[str, ...], ...] = tuple(dict.fromkeys(target_items))
        for parts in targets:
            target: ImportOwnership = ownership(parts=parts, initializer=False)
            private: bool = (
                target.role == ExemplarRoleName.MAIN
                and bool(target.tail)
                and target.tail[-1].startswith("_")
                and not target.tail[-1].startswith("__")
            )
            shares_domain: bool = (
                current.package == target.package
                and current.domain is not None
                and current.domain == target.domain
            )
            if private and not shares_domain and target_module_exists(ctx=ctx, parts=parts):
                faults.append(
                    ctx.fault_at(
                        location=fact.location,
                        message=f"import '{'.'.join(parts)}' reaches a domain-private main entry",
                    )
                )
                break
    return faults
