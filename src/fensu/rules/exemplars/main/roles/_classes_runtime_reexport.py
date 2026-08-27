"""Public custom equivalent of native classes runtime re-export policy."""

import ast

from fensu import Family, Fault, ModuleDeclarationFacts, RuleContext, ScopeName, rule


@rule(
    code="XCR504",
    family=Family.CUSTOM,
    slug="classes-runtime-reexport-equivalent",
    message="classes/ modules must not publicly re-export imported runtime symbols",
    remediation=(
        "Import runtime symbols from their defining modules and keep each classes/ module's "
        "public surface owned by its class."
    ),
)
def classes_runtime_reexport_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFR504 through public role and declaration facts."""

    del module
    if (
        ctx.scope() is ScopeName.TEST
        or not ctx.in_role("classes")
        or ctx.path.name.startswith("__init__.")
    ):
        return []
    declarations: ModuleDeclarationFacts = ctx.facts.module_declarations()
    return [
        ctx.path_fault(
            message=(
                f"classes modules must not publicly re-export imported runtime symbol '{name}'"
            )
        )
        for name in sorted(declarations.static_all_names & declarations.runtime_imported_bindings)
    ]
