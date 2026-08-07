"""Public custom equivalent of native scenario-model declaration policy."""

import ast

from fensu import Fault, RuleContext
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule


@equivalent_rule(
    core_code="FFT205",
    code="XCT205",
    slug="scenario-models-dataclasses-equivalent",
)
def scenario_models_dataclasses_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT205 through public module-declaration facts."""

    if ctx.path.name not in ctx.constraint(name="scenario_model_filenames"):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement and not fact.dataclass_class
    ]
