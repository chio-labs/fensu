"""Shape rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.shape.helpers.checks import (
    default_mutation_return,
    discarded_call_result,
    keyword_only_arguments,
    max_arguments,
    max_statements_global,
    mutable_result_model,
    parameter_mutation_in_phase_helpers,
    too_many_distinct_calls,
    too_many_locals,
    too_many_statements,
)
from strata.rules.shape.types import ShapeCode


def shape_rules() -> tuple[RuleSpec, ...]:
    """Build shape family rules."""

    return (
        RuleSpec(
            code=ShapeCode.TOO_MANY_STATEMENTS,
            family=Family.SHAPE,
            slug="too-many-statements",
            message="main functions must stay phase-shaped and below the statement limit",
            check=too_many_statements,
        ),
        RuleSpec(
            code=ShapeCode.TOO_MANY_DISTINCT_CALLS,
            family=Family.SHAPE,
            slug="too-many-distinct-calls",
            message="main functions must not coordinate too many distinct callees",
            check=too_many_distinct_calls,
        ),
        RuleSpec(
            code=ShapeCode.TOO_MANY_LOCALS,
            family=Family.SHAPE,
            slug="too-many-locals",
            message="main functions must not juggle too many local variables",
            check=too_many_locals,
        ),
        RuleSpec(
            code=ShapeCode.MAX_ARGUMENTS,
            family=Family.SHAPE,
            slug="max-arguments",
            message="functions must stay below the configured argument limit",
            check=max_arguments,
        ),
        RuleSpec(
            code=ShapeCode.MAX_STATEMENTS_GLOBAL,
            family=Family.SHAPE,
            slug="max-statements-global",
            message="functions must stay below the global statement limit",
            check=max_statements_global,
        ),
        RuleSpec(
            code=ShapeCode.DISCARDED_CALL_RESULT,
            family=Family.SHAPE,
            slug="discarded-call-result",
            message="main orchestrators must consume phase call results",
            check=discarded_call_result,
        ),
        RuleSpec(
            code=ShapeCode.PARAMETER_MUTATION_IN_PHASE_HELPERS,
            family=Family.SHAPE,
            slug="parameter-mutation-in-phase-helpers",
            message="helpers must return values instead of mutating parameters",
            check=parameter_mutation_in_phase_helpers,
            enabled_by_default=False,
        ),
        RuleSpec(
            code=ShapeCode.DEFAULT_MUTATION_RETURN,
            family=Family.SHAPE,
            slug="default-mutation-return",
            message="functions that mutate parameters must return every mutated parameter",
            check=default_mutation_return,
        ),
        RuleSpec(
            code=ShapeCode.KEYWORD_ONLY_ARGUMENTS,
            family=Family.SHAPE,
            slug="keyword-only-arguments",
            message="function parameters must be keyword-only beyond the configured threshold",
            check=keyword_only_arguments,
        ),
        RuleSpec(
            code=ShapeCode.MUTABLE_RESULT_MODEL,
            family=Family.SHAPE,
            slug="mutable-result-model",
            message="dataclass result models must be frozen",
            check=mutable_result_model,
        ),
    )
