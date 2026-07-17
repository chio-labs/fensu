"""Native fact facade delegation and fallback behavior."""

from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from strata.analysis.classes.native_fact_analysis import NativeFactAnalysis
from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from tests.unit.src.strata.analysis._test_types import FactDelegationTestCase
from tests.unit.src.strata.analysis.helpers import sentinel_fact_analysis

_: object = pytest.importorskip(NATIVE_FACT_MODULE_NAME)

_FACT_FAMILY_NAMES: tuple[str, ...] = (
    "annotations",
    "assignment_references",
    "class_declarations",
    "comments",
    "comparisons",
    "complex_comprehensions",
    "dataclasses",
    "evaluate_rule_calls",
    "function_conditionals",
    "function_contracts",
    "functions",
    "hygiene",
    "local_call_edges",
    "meaningful_returns",
    "module_declarations",
    "named_calls",
    "outer_state_mutations",
    "parameter_mutations",
    "parameter_mutation_occurrences",
    "project_calls",
    "project_functions",
    "references",
    "test_functions",
    "test_module",
    "top_level_definition_conditionals",
)
_NEW_NATIVE_FACT_METHODS: tuple[tuple[str, str], ...] = (
    ("class_declarations", "class_declaration_facts"),
    ("assignment_references", "assignment_reference_facts"),
    ("named_calls", "named_call_facts"),
    ("local_call_edges", "local_call_edge_facts"),
    ("comparisons", "comparison_facts"),
    ("parameter_mutation_occurrences", "parameter_mutation_occurrence_facts"),
)
_UNPARSEABLE_SOURCE: str = "("


@pytest.mark.parametrize(
    "test_case",
    [
        FactDelegationTestCase(
            description=f"{name} falls back to python when native parsing fails",
            method_name=name,
            expected_sentinel=name,
        )
        for name in _FACT_FAMILY_NAMES
    ],
    ids=lambda case: case.description,
)
def test_given_unparseable_source_when_reading_fact_family_then_falls_back_to_python_backend(
    test_case: FactDelegationTestCase,
    tmp_path: Path,
) -> None:
    facade: NativeFactAnalysis = NativeFactAnalysis(
        python_facts=lambda: sentinel_fact_analysis(method_names=_FACT_FAMILY_NAMES),
        path=tmp_path / "module.py",
        source=_UNPARSEABLE_SOURCE,
    )

    result: object = getattr(facade, test_case.method_name)()

    assert result == test_case.expected_sentinel


@pytest.mark.parametrize(
    "test_case",
    [
        FactDelegationTestCase(
            description=f"{method_name} calls native extension {extension_name}",
            method_name=method_name,
            expected_sentinel=method_name,
            extension_name=extension_name,
        )
        for method_name, extension_name in _NEW_NATIVE_FACT_METHODS
    ],
    ids=lambda case: case.description,
)
def test_given_parsed_program_when_reading_new_fact_family_then_calls_exact_native_extension(
    test_case: FactDelegationTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extension_name: str = cast(str, test_case.extension_name)
    native: SimpleNamespace = SimpleNamespace(
        **{extension_name: lambda program, path: test_case.expected_sentinel}
    )
    facade: NativeFactAnalysis = NativeFactAnalysis(
        python_facts=lambda: sentinel_fact_analysis(method_names=()),
        path=tmp_path / "module.py",
        source="",
        program=object(),
    )
    monkeypatch.setattr(facade, "_native", cast(ModuleType, native))

    result: object = getattr(facade, test_case.method_name)()

    assert result == test_case.expected_sentinel
