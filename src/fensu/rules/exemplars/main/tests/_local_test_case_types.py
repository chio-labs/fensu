"""Public custom equivalents of local test-case type policies."""

import ast
from pathlib import Path

from fensu import Family, Fault, ParametrizeFact, RuleContext, ScopeName, rule
from fensu.rules.exemplars.types import ExemplarTestPathName, ExemplarTestSymbol


def _local_types(*, ctx: RuleContext) -> frozenset[str]:
    path: Path = ctx.path.parent / "_test_types.py"
    declared: frozenset[str] = frozenset(
        fact.name for fact in ctx.project.dataclasses(requester=ctx.path, path=path)
    )
    module_name: str = ".".join(path.relative_to(ctx.repo_root).with_suffix("").parts)
    imported: set[str] = set()
    for fact in ctx.facts.references().imports:
        if fact.top_level and fact.from_import and ".".join(fact.module_parts) == module_name:
            imported.update(
                alias.bound_name for alias in fact.aliases if alias.imported_name in declared
            )
    return frozenset(imported)


@rule(
    code="XCT403",
    family=Family.CUSTOM,
    slug="test-case-annotation-equivalent",
    message="test_case parameters must use a local test-case dataclass annotation",
    remediation="Annotate test_case with a dataclass imported from the local _test_types.py.",
)
def test_case_annotation_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFT403 through public test and sibling dataclass facts."""

    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    local_types: frozenset[str] = _local_types(ctx=ctx)
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.test_functions()
        if fact.parametrize is not None
        and (
            ExemplarTestSymbol.TEST_CASE not in fact.parameter_names
            or fact.test_case_annotation_name not in local_types
        )
    ]


@rule(
    code="XCT413",
    family=Family.CUSTOM,
    slug="local-test-case-constructors-equivalent",
    message="pytest cases must construct dataclasses from the local _test_types.py",
    remediation=(
        "Parametrize using a dataclass imported from local _test_types.py. For framework harness "
        "inputs such as RuleCase, store their fields in the local dataclass and construct the "
        "framework object inside the test."
    ),
)
def _local_test_case_constructors_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TEST or ctx.path.name in set(ExemplarTestPathName):
        return []
    local_types: frozenset[str] = _local_types(ctx=ctx)
    faults: list[Fault] = []
    for function in ctx.facts.test_functions():
        parametrize: ParametrizeFact | None = function.parametrize
        if parametrize is None or (
            not parametrize.values_is_sequence and not parametrize.values_is_comprehension
        ):
            continue
        faults.extend(
            ctx.fault_at(location=case.location)
            for case in parametrize.cases
            if not case.dictionary and case.constructor_name not in local_types
        )
    return faults
