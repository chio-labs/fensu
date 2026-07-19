"""Native fact facade delegation and parse-failure behavior."""

from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

import fensu
from fensu.analysis.classes.semantic_fact_analysis import SemanticFactAnalysis
from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.analysis.exceptions import NativeSourceCompatibilityError
from tests.unit.src.fensu.analysis._test_types import (
    FactAnalysisOwnerTestCase,
    FactDelegationTestCase,
    NativeFactFamilyParityTestCase,
)
from tests.unit.src.fensu.analysis.helpers import fact_analysis_owners

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
            description=f"{name} rejects source when native parsing fails",
            method_name=name,
            expected_sentinel="Could not analyze",
        )
        for name in _FACT_FAMILY_NAMES
    ],
    ids=lambda case: case.description,
)
def test_given_unparseable_source_when_reading_fact_family_then_raises_parse_failure(
    test_case: FactDelegationTestCase,
    tmp_path: Path,
) -> None:
    facade: SemanticFactAnalysis = SemanticFactAnalysis(
        path=tmp_path / "module.py",
        source=_UNPARSEABLE_SOURCE,
    )

    with pytest.raises(NativeSourceCompatibilityError) as raised:
        _ = getattr(facade, test_case.method_name)()

    assert test_case.expected_sentinel in str(raised.value)


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
    facade: SemanticFactAnalysis = SemanticFactAnalysis(
        path=tmp_path / "module.py",
        source="",
        program=object(),
    )
    monkeypatch.setattr(facade, "_native", cast(ModuleType, native))

    result: object = getattr(facade, test_case.method_name)()

    assert result == test_case.expected_sentinel


@pytest.mark.parametrize(
    "test_case",
    [
        FactAnalysisOwnerTestCase(
            description="semantic facts have one concrete Python facade owner",
            expected_owners=("analysis/classes/semantic_fact_analysis.py:SemanticFactAnalysis",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_production_analysis_when_scanning_fact_protocol_then_has_one_concrete_owner(
    test_case: FactAnalysisOwnerTestCase,
) -> None:
    package_root: Path = Path(fensu.__file__).resolve().parent

    owners: tuple[str, ...] = fact_analysis_owners(root=package_root)

    assert owners == test_case.expected_owners


@pytest.mark.parametrize(
    "test_case",
    [
        NativeFactFamilyParityTestCase(
            description="every native core fact family is public and API-tested",
            expected_missing_families=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_registered_native_rules_when_checking_fact_families_then_all_are_public(
    test_case: NativeFactFamilyParityTestCase,
) -> None:
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    registrations: list[tuple[str, list[str]]] = native.native_rule_fact_families()
    required_families: set[str] = set().union(*(set(families) for _, families in registrations))
    public_families: set[str] = set(_FACT_FAMILY_NAMES).intersection(dir(SemanticFactAnalysis))
    missing: tuple[str, ...] = tuple(sorted(required_families - public_families))

    assert missing == test_case.expected_missing_families
