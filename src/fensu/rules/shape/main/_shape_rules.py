"""Shape rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.shape.types import ShapeCode


def shape_rules() -> tuple[RuleSpec, ...]:
    """Build shape family rules."""

    return (
        RuleSpec(
            code=ShapeCode.TOO_MANY_STATEMENTS,
            family=Family.SHAPE,
            slug="too-many-statements",
            message="main functions must stay phase-shaped and below the statement limit",
            remediation="Extract cohesive phases into helpers that return explicit result models.",
        ),
        RuleSpec(
            code=ShapeCode.TOO_MANY_DISTINCT_CALLS,
            family=Family.SHAPE,
            slug="too-many-distinct-calls",
            message="main functions must not coordinate too many distinct callees",
            remediation=(
                "Group related work into named phase helpers and keep main/ as a short ordered "
                "flow."
            ),
        ),
        RuleSpec(
            code=ShapeCode.TOO_MANY_LOCALS,
            family=Family.SHAPE,
            slug="too-many-locals",
            message="main functions must not juggle too many local variables",
            remediation=(
                "Let each extracted phase own its intermediates and return one structured result."
            ),
        ),
        RuleSpec(
            code=ShapeCode.MAX_ARGUMENTS,
            family=Family.SHAPE,
            slug="max-arguments",
            message="functions must stay below the configured argument limit",
            remediation=(
                "Reduce the function's responsibility or group cohesive inputs into a typed model."
            ),
        ),
        RuleSpec(
            code=ShapeCode.MAX_STATEMENTS_GLOBAL,
            family=Family.SHAPE,
            slug="max-statements-global",
            message="functions must stay below the global statement limit",
            remediation=(
                "Split the function at a meaningful phase boundary with explicit inputs and "
                "outputs."
            ),
        ),
        RuleSpec(
            code=ShapeCode.MEANINGFUL_PROJECT_RESULT_DISCARDED,
            family=Family.SHAPE,
            slug="meaningful-project-result-discarded",
            message="main orchestrators must consume meaningful project-local call results",
            remediation=(
                "Assign, return, or explicitly discard the phase result with _ = call(...)."
            ),
        ),
        RuleSpec(
            code=ShapeCode.PARAMETER_MUTATION_IN_PHASE_HELPERS,
            family=Family.SHAPE,
            slug="parameter-mutation-in-phase-helpers",
            message="helpers must return values instead of mutating parameters",
            remediation="Return a new or updated value so dataflow remains visible to the caller.",
            enabled_by_default=False,
        ),
        RuleSpec(
            code=ShapeCode.DEFAULT_MUTATION_RETURN,
            family=Family.SHAPE,
            slug="default-mutation-return",
            message="functions that mutate parameters must return every mutated parameter",
            remediation=(
                "Return each mutated parameter explicitly, or avoid parameter mutation and "
                "return a new value."
            ),
        ),
        RuleSpec(
            code=ShapeCode.KEYWORD_ONLY_ARGUMENTS,
            family=Family.SHAPE,
            slug="keyword-only-arguments",
            message="functions beyond the parameter threshold must be entirely keyword-only",
            remediation=(
                "Insert * before the first non-receiver parameter so every call argument names "
                "its meaning."
            ),
        ),
        RuleSpec(
            code=ShapeCode.NO_OUTER_STATE_MUTATION,
            family=Family.SHAPE,
            slug="no-outer-state-mutation",
            message="functions must not mutate module-global or closure-captured state",
            remediation=(
                "Pass state explicitly and return the updated value instead of mutating outer "
                "scope."
            ),
        ),
        RuleSpec(
            code=ShapeCode.NO_COMPLEX_COMPREHENSIONS,
            family=Family.SHAPE,
            slug="no-complex-comprehensions",
            message="nested or multi-generator comprehensions hide control flow and data shapes",
            remediation=(
                "Extract a named helper when the transformation has a coherent purpose. For "
                "one-off local logic, use simple statements with named intermediate values "
                "instead of nested comprehension control flow."
            ),
        ),
        RuleSpec(
            code=ShapeCode.MUTABLE_RESULT_MODEL,
            family=Family.SHAPE,
            slug="mutable-result-model",
            message="dataclass result models must be frozen",
            remediation="Declare the shared result model with @dataclass(frozen=True).",
        ),
    )
