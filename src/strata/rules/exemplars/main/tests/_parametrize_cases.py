"""Public custom equivalents of native pytest-parametrize case policies."""

import ast

from strata import Family, Fault, ParametrizeFact, RuleContext, ScopeName, rule
from strata.rules.exemplars.types import ExemplarTestLimit, ExemplarTestPathName


@rule(
    code="XCT412",
    family=Family.CUSTOM,
    slug="no-dict-test-cases-equivalent",
    message="pytest cases must use typed dataclasses instead of dictionaries",
    remediation="Define a local frozen test-case dataclass and construct one instance per case.",
)
def no_dict_test_cases_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFT412 through public parametrize case facts."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    faults: list[Fault] = []
    for fact in ctx.facts.test_functions():
        parametrize: ParametrizeFact | None = fact.parametrize
        if (
            parametrize is None
            or parametrize.argument_count < int(ExemplarTestLimit.MINIMUM_PARAMETRIZE_ARGUMENTS)
            or not parametrize.values_is_sequence
        ):
            continue
        faults.extend(
            ctx.fault_at(location=case.location) for case in parametrize.cases if case.dictionary
        )
    return faults


@rule(
    code="XCT414",
    family=Family.CUSTOM,
    slug="description-lambda-ids-equivalent",
    message="pytest case ids must come from each test case description",
    remediation=(
        "Use ids=lambda case: case.description so failures identify the behavior clearly."
    ),
)
def _description_lambda_ids_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None
        and fact.parametrize.argument_count >= int(ExemplarTestLimit.MINIMUM_PARAMETRIZE_ARGUMENTS)
        and (fact.parametrize.values_is_sequence or fact.parametrize.values_is_comprehension)
        and not fact.parametrize.description_lambda_ids
    ]
