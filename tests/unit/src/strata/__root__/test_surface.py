"""Tests for the strata public API surface."""

from __future__ import annotations

import pytest

import strata
from strata import Threshold
from tests.unit.src.strata.__root__._test_types import PublicSurfaceTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        PublicSurfaceTestCase(
            description="strata exports the complete public rule authoring surface",
            expected_all=(
                "AnnotationFacts",
                "AttributeReferenceFact",
                "CommentFact",
                "DataclassFact",
                "DiscardedProjectCallFact",
                "EvaluateRuleCallFact",
                "FactAnalysis",
                "Fault",
                "Family",
                "FunctionConditionalFact",
                "FunctionFacts",
                "FunctionMetricFact",
                "HygieneFacts",
                "ImportAliasFact",
                "ImportFact",
                "MeaningfulReturnFact",
                "MissingLocalAnnotationFact",
                "MissingParameterAnnotationFact",
                "MissingReturnAnnotationFact",
                "MissingVariableAnnotationFact",
                "ModuleDeclarationFacts",
                "ModuleStatementFact",
                "NamedCallFact",
                "NodeId",
                "OuterStateMutationFact",
                "ParameterMutationFact",
                "ParametrizeCaseFact",
                "ParametrizeDimensionFact",
                "ParametrizeFact",
                "ProjectAnalysis",
                "ProjectCallFacts",
                "ProjectDependency",
                "ProjectFunctionFact",
                "PytestFunctionFact",
                "PytestModuleFacts",
                "ReferenceFacts",
                "RelationAnalysis",
                "RuleCase",
                "RuleCaseForm",
                "RuleContext",
                "RuleFile",
                "RuleResult",
                "RuleTestAssociationFact",
                "Severity",
                "SourceLocation",
                "SourcePosition",
                "SourceRange",
                "StaticReferenceFact",
                "SyntaxAnalysis",
                "SyntaxHandle",
                "TextAnalysis",
                "Threshold",
                "TypeDeclarationFact",
                "evaluate_rule",
                "rule",
            ),
            expected_threshold_value="max_statements",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_strata_package_when_reading_all_then_matches_expected(
    test_case: PublicSurfaceTestCase,
) -> None:
    actual_all: tuple[str, ...] = tuple(strata.__all__)

    assert actual_all == test_case.expected_all


@pytest.mark.parametrize(
    "test_case",
    [
        PublicSurfaceTestCase(
            description="every exported name is importable from the top level",
            expected_all=(
                "AnnotationFacts",
                "AttributeReferenceFact",
                "CommentFact",
                "DataclassFact",
                "DiscardedProjectCallFact",
                "EvaluateRuleCallFact",
                "FactAnalysis",
                "Fault",
                "Family",
                "FunctionConditionalFact",
                "FunctionFacts",
                "FunctionMetricFact",
                "HygieneFacts",
                "ImportAliasFact",
                "ImportFact",
                "MeaningfulReturnFact",
                "MissingLocalAnnotationFact",
                "MissingParameterAnnotationFact",
                "MissingReturnAnnotationFact",
                "MissingVariableAnnotationFact",
                "ModuleDeclarationFacts",
                "ModuleStatementFact",
                "NamedCallFact",
                "NodeId",
                "OuterStateMutationFact",
                "ParameterMutationFact",
                "ParametrizeCaseFact",
                "ParametrizeDimensionFact",
                "ParametrizeFact",
                "ProjectAnalysis",
                "ProjectCallFacts",
                "ProjectDependency",
                "ProjectFunctionFact",
                "PytestFunctionFact",
                "PytestModuleFacts",
                "ReferenceFacts",
                "RelationAnalysis",
                "RuleCase",
                "RuleCaseForm",
                "RuleContext",
                "RuleFile",
                "RuleResult",
                "RuleTestAssociationFact",
                "Severity",
                "SourceLocation",
                "SourcePosition",
                "SourceRange",
                "StaticReferenceFact",
                "SyntaxAnalysis",
                "SyntaxHandle",
                "TextAnalysis",
                "Threshold",
                "TypeDeclarationFact",
                "evaluate_rule",
                "rule",
            ),
            expected_threshold_value="max_statements",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_public_names_when_importing_then_all_resolve(
    test_case: PublicSurfaceTestCase,
) -> None:
    resolved: list[object | None] = [getattr(strata, name, None) for name in test_case.expected_all]
    threshold: Threshold = Threshold.MAX_STATEMENTS

    assert all(item is not None for item in resolved)
    assert len(resolved) == len(test_case.expected_all)
    assert threshold.value == test_case.expected_threshold_value
