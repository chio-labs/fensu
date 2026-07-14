"""Native pass-through fact facade delegation behavior."""

import pytest

from strata.analysis.classes.native_fact_analysis import NativeFactAnalysis
from tests.unit.src.strata.analysis._test_types import FactDelegationTestCase
from tests.unit.src.strata.analysis.helpers import sentinel_fact_analysis

_FACT_FAMILY_NAMES: tuple[str, ...] = (
    "annotations",
    "comments",
    "complex_comprehensions",
    "dataclasses",
    "evaluate_rule_calls",
    "function_conditionals",
    "function_contracts",
    "functions",
    "hygiene",
    "meaningful_returns",
    "module_declarations",
    "outer_state_mutations",
    "parameter_mutations",
    "project_calls",
    "project_functions",
    "references",
    "test_functions",
    "test_module",
    "top_level_definition_conditionals",
)


@pytest.mark.parametrize(
    "test_case",
    [
        FactDelegationTestCase(
            description=f"{name} delegates to the python implementation",
            method_name=name,
            expected_sentinel=name,
        )
        for name in _FACT_FAMILY_NAMES
    ],
    ids=lambda case: case.description,
)
def test_given_pass_through_facade_when_reading_fact_family_then_delegates_to_python_backend(
    test_case: FactDelegationTestCase,
) -> None:
    facade: NativeFactAnalysis = NativeFactAnalysis(
        python_facts=sentinel_fact_analysis(method_names=_FACT_FAMILY_NAMES)
    )

    result: object = getattr(facade, test_case.method_name)()

    assert result == test_case.expected_sentinel
