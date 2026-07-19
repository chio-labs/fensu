"""Public custom equivalent of project-owned main-entry use policy."""

import ast

from fensu import ExecutionOwner, Family, Fault, RuleContext, rule
from fensu.rules.exemplars._helpers.non_file_rules import public_main_entry_external_use_impl


@rule(
    code="XCL105",
    family=Family.CUSTOM,
    slug="public-main-entry-external-use-equivalent",
    message="public main entries must have an importer outside their owning domain",
    remediation=(
        "Prefix the entry module filename with '_' until another domain or tooling imports it."
    ),
    execution_owner=ExecutionOwner.PROJECT,
)
def public_main_entry_external_use_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express FFL105 through public project and semantic-fact APIs."""

    return public_main_entry_external_use_impl(module=module, ctx=ctx)
