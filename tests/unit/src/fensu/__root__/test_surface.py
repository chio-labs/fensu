"""Tests for the fensu public API surface."""

from __future__ import annotations

import subprocess
import sys

import pytest

import fensu
from fensu import Threshold
from tests.unit.src.fensu.__root__._test_types import (
    LazyPublicSurfaceTestCase,
    PublicSurfaceTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        PublicSurfaceTestCase(
            description="fensu exports the complete public rule authoring surface",
            expected_all=(
                "AnnotationFacts",
                "AssignmentReferenceFact",
                "AttributeReferenceFact",
                "ClassDeclarationFact",
                "ClassMethodFact",
                "CommentFact",
                "ComparisonFact",
                "ContractBehavior",
                "DataclassFact",
                "DefinitionIdentity",
                "DiscardedProjectCallFact",
                "EvaluateRuleCallFact",
                "ExecutionOwner",
                "FactAnalysis",
                "Fault",
                "Family",
                "FunctionConditionalFact",
                "FunctionFacts",
                "FunctionMetricFact",
                "HygieneFacts",
                "ImportAliasFact",
                "ImportFact",
                "LiteralArgumentFact",
                "LocalCallEdgeFact",
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
                "ParameterMutationOccurrenceFact",
                "ParametrizeCaseFact",
                "ParametrizeDimensionFact",
                "ParametrizeFact",
                "ProjectAnalysis",
                "ProjectCallFacts",
                "ProjectDependency",
                "ProjectFunctionFact",
                "PytestFunctionFact",
                "PytestModuleFacts",
                "QualifiedReferenceFact",
                "ReferenceFacts",
                "ReturnAnnotationCategory",
                "RelationAnalysis",
                "RuleCase",
                "RuleCaseForm",
                "RuleContext",
                "RuleFile",
                "RuleOption",
                "RuleResult",
                "RuleTestAssociationFact",
                "ScopeName",
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
def test_given_fensu_package_when_reading_all_then_matches_expected(
    test_case: PublicSurfaceTestCase,
) -> None:
    actual_all: tuple[str, ...] = tuple(fensu.__all__)

    assert actual_all == test_case.expected_all


@pytest.mark.parametrize(
    "test_case",
    [
        PublicSurfaceTestCase(
            description="every exported name is importable from the top level",
            expected_all=(
                "AnnotationFacts",
                "AssignmentReferenceFact",
                "AttributeReferenceFact",
                "ClassDeclarationFact",
                "ClassMethodFact",
                "CommentFact",
                "ComparisonFact",
                "ContractBehavior",
                "DataclassFact",
                "DefinitionIdentity",
                "DiscardedProjectCallFact",
                "EvaluateRuleCallFact",
                "ExecutionOwner",
                "FactAnalysis",
                "Fault",
                "Family",
                "FunctionConditionalFact",
                "FunctionFacts",
                "FunctionMetricFact",
                "HygieneFacts",
                "ImportAliasFact",
                "ImportFact",
                "LiteralArgumentFact",
                "LocalCallEdgeFact",
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
                "ParameterMutationOccurrenceFact",
                "ParametrizeCaseFact",
                "ParametrizeDimensionFact",
                "ParametrizeFact",
                "ProjectAnalysis",
                "ProjectCallFacts",
                "ProjectDependency",
                "ProjectFunctionFact",
                "PytestFunctionFact",
                "PytestModuleFacts",
                "QualifiedReferenceFact",
                "ReferenceFacts",
                "ReturnAnnotationCategory",
                "RelationAnalysis",
                "RuleCase",
                "RuleCaseForm",
                "RuleContext",
                "RuleFile",
                "RuleResult",
                "RuleTestAssociationFact",
                "ScopeName",
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
    resolved: list[object | None] = [getattr(fensu, name, None) for name in test_case.expected_all]
    threshold: Threshold = Threshold.MAX_STATEMENTS

    assert all(item is not None for item in resolved)
    assert len(resolved) == len(test_case.expected_all)
    assert threshold.value == test_case.expected_threshold_value


@pytest.mark.parametrize(
    "test_case",
    [
        LazyPublicSurfaceTestCase(
            description="bare package import defers the rule evaluation harness",
            expected_absent_module="fensu.rules.testing.main.evaluate_rule",
            expected_return_code=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_bare_package_import_when_loading_then_defers_testing_harness(
    test_case: LazyPublicSurfaceTestCase,
) -> None:
    script: str = (
        "import sys; import fensu; raise SystemExit("
        f"int({test_case.expected_absent_module!r} in sys.modules))"
    )

    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == test_case.expected_return_code
