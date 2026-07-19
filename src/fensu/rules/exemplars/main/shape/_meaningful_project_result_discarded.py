"""Public custom equivalent of native meaningful-result consumption policy."""

import ast

from fensu import Family, Fault, ProjectFunctionFact, RuleContext, rule


@rule(
    code="XCS101",
    family=Family.CUSTOM,
    slug="meaningful-project-result-discarded-equivalent",
    message="main orchestrators must consume meaningful project-local call results",
    remediation="Assign, return, or explicitly discard the phase result with _ = call(...).",
)
def meaningful_project_result_discarded_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express FFS101 through public project call and function facts."""

    del module
    if not ctx.is_main_module():
        return []
    local: tuple[ProjectFunctionFact, ...] = ctx.facts.project_functions()
    faults: list[Fault] = []
    for call in ctx.facts.project_calls().discarded_calls:
        function: ProjectFunctionFact | None = (
            next((item for item in local if item.name == call.function_name), None)
            if call.module_name is None
            else ctx.project.module_function(
                requester=ctx.path,
                module_name=call.module_name,
                function_name=call.function_name,
            )
        )
        if function is not None and function.meaningful_result:
            faults.append(ctx.fault_at(location=call.location))
    return faults
