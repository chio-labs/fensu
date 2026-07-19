"""Tests for static custom-rule harness facts and associations."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.analysis.main.associate_rule_tests import associate_rule_tests
from strata.analysis.models import (
    EvaluateRuleCallFact,
    ParametrizeDimensionFact,
    ParametrizeFact,
    PytestFunctionFact,
    RuleTestAssociationFact,
)
from strata.analysis.types import Analysis
from tests.unit.src.strata.analysis._test_types import (
    HarnessUseFactMatrixTestCase,
    HarnessUseFactTestCase,
    RuleTestAssociationFactMatrixTestCase,
    RuleTestAssociationFactTestCase,
)
from tests.unit.src.strata.analysis.helpers import (
    build_module_analyses,
    build_test_analysis,
    rule_case_location_lines,
)

_HARNESS_FACT_CASES: tuple[HarnessUseFactTestCase, ...] = (
    HarnessUseFactTestCase(
        description="stacked dimensions count only literal RuleCase values and preserve singular fact",
        source=(
            "from strata import RuleCase, evaluate_rule\n"
            "from scripts.rules.policy import no_global\n\n"
            "@pytest.mark.parametrize('backend', ['left', 'right'])\n"
            "@pytest.mark.parametrize(\n"
            "    'test_case',\n"
            "    [RuleCase(description='one', source='x = 1', expected_fault_count=0),\n"
            "     RuleCase(description='two', source='x = 2', expected_fault_count=1)],\n"
            ")\n"
            "def test_given_source_when_checking_then_matches(test_case, backend) -> None:\n"
            "    first = evaluate_rule(rule=no_global, test_case=test_case)\n"
            "    second = evaluate_rule(rule=no_global, test_case=test_case)\n"
        ),
        expected_singular_parameter="backend",
        expected_dimension_parameters=(("backend",), ("test_case",)),
        expected_dimension_case_counts=(0, 2),
        expected_dimension_unknown=(True, False),
        expected_call_lines=(11, 12),
        expected_owner_names=(
            "test_given_source_when_checking_then_matches",
            "test_given_source_when_checking_then_matches",
        ),
        expected_rule_references=(
            ("scripts.rules.policy", "no_global"),
            ("scripts.rules.policy", "no_global"),
        ),
        expected_forms=("parameter", "parameter"),
        expected_case_counts=(2, 2),
        expected_case_lines=((7, 8), (7, 8)),
        expected_unknown=(False, False),
    ),
    HarnessUseFactTestCase(
        description="aliases module qualification and a literal tuple resolve statically",
        source=(
            "import strata as st\n"
            "import scripts.rules.policy as policy\n"
            "from strata import RuleCase as Case, evaluate_rule as check\n"
            "from scripts.rules.other import second_rule as other\n\n"
            "@pytest.mark.parametrize(\n"
            "    'test_case',\n"
            "    (Case(description='one', source='x = 1', expected_fault_count=0),),\n"
            ")\n"
            "def test_given_source_when_checking_then_matches(test_case) -> None:\n"
            "    first = st.evaluate_rule(rule=policy.no_global, test_case=test_case)\n"
            "    second = check(rule=other, test_case=test_case)\n"
        ),
        expected_singular_parameter="test_case",
        expected_dimension_parameters=(("test_case",),),
        expected_dimension_case_counts=(1,),
        expected_dimension_unknown=(False,),
        expected_call_lines=(11, 12),
        expected_owner_names=(
            "test_given_source_when_checking_then_matches",
            "test_given_source_when_checking_then_matches",
        ),
        expected_rule_references=(
            ("scripts.rules.policy", "no_global"),
            ("scripts.rules.other", "second_rule"),
        ),
        expected_forms=("parameter", "parameter"),
        expected_case_counts=(1, 1),
        expected_case_lines=((8,), (8,)),
        expected_unknown=(False, False),
    ),
    HarnessUseFactTestCase(
        description="a uniquely assigned module literal sequence is statically visible",
        source=(
            "from strata import RuleCase as Case, evaluate_rule\n"
            "from scripts.rules.policy import no_global\n\n"
            "CASES = (\n"
            "    Case(description='one', source='x = 1', expected_fault_count=0),\n"
            "    Case(description='two', source='x = 2', expected_fault_count=1),\n"
            ")\n\n"
            "@pytest.mark.parametrize('test_case', CASES)\n"
            "def test_given_source_when_checking_then_matches(test_case) -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=test_case)\n"
        ),
        expected_singular_parameter="test_case",
        expected_dimension_parameters=(("test_case",),),
        expected_dimension_case_counts=(2,),
        expected_dimension_unknown=(False,),
        expected_call_lines=(11,),
        expected_owner_names=("test_given_source_when_checking_then_matches",),
        expected_rule_references=(("scripts.rules.policy", "no_global"),),
        expected_forms=("parameter",),
        expected_case_counts=(2,),
        expected_case_lines=((5, 6),),
        expected_unknown=(False,),
    ),
    HarnessUseFactTestCase(
        description="a direct nonparametrized RuleCase call proves one case",
        source=(
            "from strata import RuleCase, evaluate_rule\n"
            "from scripts.rules.policy import no_global\n\n"
            "def test_given_source_when_checking_then_matches() -> None:\n"
            "    result = evaluate_rule(\n"
            "        rule=no_global,\n"
            "        test_case=RuleCase(description='one', source='x = 1', expected_fault_count=0),\n"
            "    )\n"
        ),
        expected_singular_parameter=None,
        expected_dimension_parameters=(),
        expected_dimension_case_counts=(),
        expected_dimension_unknown=(),
        expected_call_lines=(5,),
        expected_owner_names=("test_given_source_when_checking_then_matches",),
        expected_rule_references=(("scripts.rules.policy", "no_global"),),
        expected_forms=("literal",),
        expected_case_counts=(1,),
        expected_case_lines=((7,),),
        expected_unknown=(False,),
    ),
    HarnessUseFactTestCase(
        description="dynamic rows wrappers locals and selected rules prove no cases",
        source=(
            "from strata import RuleCase, evaluate_rule\n"
            "from scripts.rules.policy import no_global\n\n"
            "@pytest.mark.parametrize('test_case', load_cases())\n"
            "def test_given_dynamic_when_checking_then_unknown(test_case) -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=test_case)\n\n"
            "@pytest.mark.parametrize('test_case', [pytest.param(RuleCase(description='one', source='x = 1', expected_fault_count=0))])\n"
            "def test_given_wrapper_when_checking_then_unknown(test_case) -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=test_case)\n\n"
            "@pytest.mark.parametrize('test_case, backend', [(RuleCase(description='one', source='x = 1', expected_fault_count=0), 'left')])\n"
            "def test_given_row_when_checking_then_unknown(test_case, backend) -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=test_case)\n\n"
            "def test_given_local_when_checking_then_unknown() -> None:\n"
            "    case = RuleCase(description='one', source='x = 1', expected_fault_count=0)\n"
            "    result = evaluate_rule(rule=no_global, test_case=case)\n\n"
            "def test_given_selected_rule_when_checking_then_unresolved() -> None:\n"
            "    selected = no_global\n"
            "    result = evaluate_rule(rule=selected, test_case=RuleCase(description='one', source='x = 1', expected_fault_count=0))\n"
        ),
        expected_singular_parameter="test_case",
        expected_dimension_parameters=(("test_case",),),
        expected_dimension_case_counts=(0,),
        expected_dimension_unknown=(True,),
        expected_call_lines=(6, 10, 14, 18, 22),
        expected_owner_names=(
            "test_given_dynamic_when_checking_then_unknown",
            "test_given_wrapper_when_checking_then_unknown",
            "test_given_row_when_checking_then_unknown",
            "test_given_local_when_checking_then_unknown",
            "test_given_selected_rule_when_checking_then_unresolved",
        ),
        expected_rule_references=(
            ("scripts.rules.policy", "no_global"),
            ("scripts.rules.policy", "no_global"),
            ("scripts.rules.policy", "no_global"),
            ("scripts.rules.policy", "no_global"),
            (None, None),
        ),
        expected_forms=("parameter", "parameter", "parameter", "local", "literal"),
        expected_case_counts=(0, 0, 0, 0, 1),
        expected_case_lines=((), (), (), (), (22,)),
        expected_unknown=(True, True, True, True, False),
    ),
    HarnessUseFactTestCase(
        description="shadowed harness and constructor bindings are rejected conservatively",
        source=(
            "from strata import RuleCase, evaluate_rule\n"
            "from scripts.rules.policy import no_global\n\n"
            "def test_given_harness_parameter_when_calling_then_not_recognized(evaluate_rule) -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=None)\n\n"
            "def test_given_rule_parameter_when_calling_then_unresolved(no_global) -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=RuleCase(description='one', source='x = 1', expected_fault_count=0))\n\n"
            "def test_given_constructor_parameter_when_calling_then_unknown(RuleCase) -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=RuleCase())\n"
        ),
        expected_singular_parameter=None,
        expected_dimension_parameters=(),
        expected_dimension_case_counts=(),
        expected_dimension_unknown=(),
        expected_call_lines=(8, 11),
        expected_owner_names=(
            "test_given_rule_parameter_when_calling_then_unresolved",
            "test_given_constructor_parameter_when_calling_then_unknown",
        ),
        expected_rule_references=((None, None), ("scripts.rules.policy", "no_global")),
        expected_forms=("literal", "dynamic"),
        expected_case_counts=(1, 0),
        expected_case_lines=((8,), ()),
        expected_unknown=(False, True),
    ),
)


_ASSOCIATION_CASES: tuple[RuleTestAssociationFactTestCase, ...] = (
    RuleTestAssociationFactTestCase(
        description="duplicate calls deduplicate cases while retaining call locations",
        test_source=_HARNESS_FACT_CASES[0].source,
        module_names=("scripts.rules.policy",),
        module_sources=(
            "from strata import rule\n@rule(code='X1')\ndef no_global(module, ctx):\n    return []\n",
        ),
        expected_rule_references=(("scripts.rules.policy", "no_global"),),
        expected_case_counts=(2,),
        expected_call_counts=(2,),
        expected_unknown=(False,),
    ),
    RuleTestAssociationFactTestCase(
        description="one test using two rules produces separate exact associations",
        test_source=_HARNESS_FACT_CASES[1].source,
        module_names=("scripts.rules.policy", "scripts.rules.other"),
        module_sources=(
            "from strata import rule\n@rule(code='X1')\ndef no_global(module, ctx):\n    return []\n",
            "from strata import rule\n@rule(code='X2')\ndef second_rule(module, ctx):\n    return []\n",
        ),
        expected_rule_references=(
            ("scripts.rules.other", "second_rule"),
            ("scripts.rules.policy", "no_global"),
        ),
        expected_case_counts=(1, 1),
        expected_call_counts=(1, 1),
        expected_unknown=(False, False),
    ),
    RuleTestAssociationFactTestCase(
        description="an aliased re-export resolves to the decorated rule declaration",
        test_source=(
            "from strata import RuleCase, evaluate_rule\n"
            "from rules.surface import exported as policy\n\n"
            "def test_given_source_when_checking_then_matches() -> None:\n"
            "    result = evaluate_rule(rule=policy, test_case=RuleCase(description='one', source='x = 1', expected_fault_count=0))\n"
        ),
        module_names=("rules.surface", "rules.actual"),
        module_sources=(
            "from rules.actual import no_global as exported\n__all__ = ['exported']\n",
            "from strata import rule\n@rule(code='X1')\ndef no_global(module, ctx):\n    return []\n",
        ),
        expected_rule_references=(("rules.actual", "no_global"),),
        expected_case_counts=(1,),
        expected_call_counts=(1,),
        expected_unknown=(False,),
    ),
    RuleTestAssociationFactTestCase(
        description="a re-export cycle is unresolved and contributes no association",
        test_source=(
            "from strata import RuleCase, evaluate_rule\n"
            "from rules.first import policy\n\n"
            "def test_given_source_when_checking_then_unknown() -> None:\n"
            "    result = evaluate_rule(rule=policy, test_case=RuleCase(description='one', source='x = 1', expected_fault_count=0))\n"
        ),
        module_names=("rules.first", "rules.second"),
        module_sources=(
            "from rules.second import policy\n__all__ = ['policy']\n",
            "from rules.first import policy\n__all__ = ['policy']\n",
        ),
        expected_rule_references=(),
        expected_case_counts=(),
        expected_call_counts=(),
        expected_unknown=(),
    ),
    RuleTestAssociationFactTestCase(
        description="a shadowed re-export is unresolved and contributes no association",
        test_source=(
            "from strata import RuleCase, evaluate_rule\n"
            "from rules.surface import no_global\n\n"
            "def test_given_source_when_checking_then_unknown() -> None:\n"
            "    result = evaluate_rule(rule=no_global, test_case=RuleCase(description='one', source='x = 1', expected_fault_count=0))\n"
        ),
        module_names=("rules.surface", "rules.actual"),
        module_sources=(
            "from rules.actual import no_global\nno_global = object()\n",
            "from strata import rule\n@rule(code='X1')\ndef no_global(module, ctx):\n    return []\n",
        ),
        expected_rule_references=(),
        expected_case_counts=(),
        expected_call_counts=(),
        expected_unknown=(),
    ),
    RuleTestAssociationFactTestCase(
        description="an import and rule code string without a harness call prove nothing",
        test_source=(
            "from rules.actual import no_global\n\n"
            "def test_given_code_when_checking_then_mentions_only() -> None:\n"
            "    code = 'X1'\n"
        ),
        module_names=("rules.actual",),
        module_sources=(
            "from strata import rule\n@rule(code='X1')\ndef no_global(module, ctx):\n    return []\n",
        ),
        expected_rule_references=(),
        expected_case_counts=(),
        expected_call_counts=(),
        expected_unknown=(),
    ),
)


@pytest.mark.parametrize(
    "test_case",
    [
        HarnessUseFactMatrixTestCase(
            description="covers accepted and conservatively rejected harness syntax",
            cases=_HARNESS_FACT_CASES,
            expected_case_count=6,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_harness_syntax_when_querying_facts_then_returns_static_use_metadata(
    tmp_path: Path,
    test_case: HarnessUseFactMatrixTestCase,
) -> None:
    scenario_count: int = 0
    for scenario in test_case.cases:
        analysis: Analysis = build_test_analysis(
            path=tmp_path / f"test_policy_{scenario_count}.py",
            source=scenario.source,
        )
        functions: tuple[PytestFunctionFact, ...] = analysis.facts.test_functions()
        first_parametrize: ParametrizeFact | None = functions[0].parametrize
        dimensions: tuple[ParametrizeDimensionFact, ...] = functions[0].parametrize_dimensions
        calls: tuple[EvaluateRuleCallFact, ...] = analysis.facts.evaluate_rule_calls()

        assert (
            getattr(first_parametrize, "parameter_name", None)
            == scenario.expected_singular_parameter
        )
        assert tuple(dimension.parameter_names for dimension in dimensions) == (
            scenario.expected_dimension_parameters
        )
        assert tuple(dimension.provable_rule_case_count for dimension in dimensions) == (
            scenario.expected_dimension_case_counts
        )
        assert tuple(dimension.unknown_rule_case_count for dimension in dimensions) == (
            scenario.expected_dimension_unknown
        )
        assert tuple(call.location.line for call in calls) == scenario.expected_call_lines
        assert tuple(call.test_function_name for call in calls) == scenario.expected_owner_names
        assert (
            tuple(
                (
                    getattr(call.rule_reference, "module_name", None),
                    getattr(call.rule_reference, "symbol_name", None),
                )
                for call in calls
            )
            == scenario.expected_rule_references
        )
        assert tuple(call.test_case_form.value for call in calls) == scenario.expected_forms
        assert tuple(call.provable_case_count for call in calls) == scenario.expected_case_counts
        assert rule_case_location_lines(calls) == scenario.expected_case_lines
        assert tuple(call.unknown_case_count for call in calls) == scenario.expected_unknown
        scenario_count += 1

    assert scenario_count == test_case.expected_case_count


@pytest.mark.parametrize(
    "test_case",
    [
        RuleTestAssociationFactMatrixTestCase(
            description="covers exact deduplication re-exports cycles and shadowing",
            cases=_ASSOCIATION_CASES,
            expected_case_count=6,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_harness_calls_when_associating_rules_then_resolves_and_deduplicates_conservatively(
    tmp_path: Path,
    test_case: RuleTestAssociationFactMatrixTestCase,
) -> None:
    scenario_count: int = 0
    for scenario in test_case.cases:
        test_analysis: Analysis = build_test_analysis(
            path=tmp_path / f"test_policy_{scenario_count}.py",
            source=scenario.test_source,
        )
        modules: dict[str, Analysis] = build_module_analyses(
            root=tmp_path,
            module_names=scenario.module_names,
            module_sources=scenario.module_sources,
        )
        associations: tuple[RuleTestAssociationFact, ...] = associate_rule_tests(
            calls=test_analysis.facts.evaluate_rule_calls(),
            modules=modules,
        )

        assert (
            tuple(
                (fact.rule_reference.module_name, fact.rule_reference.symbol_name)
                for fact in associations
            )
            == scenario.expected_rule_references
        )
        assert tuple(fact.provable_case_count for fact in associations) == (
            scenario.expected_case_counts
        )
        assert tuple(len(fact.call_locations) for fact in associations) == (
            scenario.expected_call_counts
        )
        assert tuple(fact.unknown_case_count for fact in associations) == (
            scenario.expected_unknown
        )
        scenario_count += 1

    assert scenario_count == test_case.expected_case_count
