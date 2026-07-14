"""Native-backend fact facade delegating unported families to Python."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from strata.analysis.models import (
        AnnotationFacts,
        CommentFact,
        DataclassFact,
        EvaluateRuleCallFact,
        FunctionConditionalFact,
        FunctionContractFact,
        FunctionFacts,
        HygieneFacts,
        MeaningfulReturnFact,
        ModuleDeclarationFacts,
        OuterStateMutationFact,
        ParameterMutationFact,
        ProjectCallFacts,
        ProjectFunctionFact,
        PytestFunctionFact,
        PytestModuleFacts,
        ReferenceFacts,
        SourceLocation,
    )
    from strata.analysis.types import FactAnalysis


class NativeFactAnalysis:
    """Semantic file facts served natively, family by family, as ports land."""

    def __init__(self, *, python_facts: FactAnalysis) -> None:
        """Bind the Python fact implementation used for unported families."""

        self._python_facts: FactAnalysis = python_facts

    def annotations(self) -> AnnotationFacts:
        """Return missing function and local annotation facts."""

        return self._python_facts.annotations()

    def comments(self) -> tuple[CommentFact, ...]:
        """Return source comments in token order."""

        return self._python_facts.comments()

    def dataclasses(self) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass declarations and field metadata."""

        return self._python_facts.dataclasses()

    def evaluate_rule_calls(self) -> tuple[EvaluateRuleCallFact, ...]:
        """Return statically recognized public rule-harness calls."""

        return self._python_facts.evaluate_rule_calls()

    def complex_comprehensions(self) -> tuple[SourceLocation, ...]:
        """Return complex comprehension locations."""

        return self._python_facts.complex_comprehensions()

    def function_conditionals(self) -> tuple[FunctionConditionalFact, ...]:
        """Return conditional control flow grouped by owning function."""

        return self._python_facts.function_conditionals()

    def functions(self) -> FunctionFacts:
        """Return reusable structural function metrics."""

        return self._python_facts.functions()

    def function_contracts(self) -> tuple[FunctionContractFact, ...]:
        """Return descriptive name, annotation, yield, and return facts."""

        return self._python_facts.function_contracts()

    def hygiene(self) -> HygieneFacts:
        """Return syntax-based hygiene facts."""

        return self._python_facts.hygiene()

    def meaningful_returns(
        self, *, name_patterns: tuple[str, ...] = ()
    ) -> tuple[MeaningfulReturnFact, ...]:
        """Return the first meaningful return owned by each function."""

        return self._python_facts.meaningful_returns(name_patterns=name_patterns)

    def module_declarations(self) -> ModuleDeclarationFacts:
        """Return module statements and classified declarations."""

        return self._python_facts.module_declarations()

    def outer_state_mutations(self) -> tuple[OuterStateMutationFact, ...]:
        """Return direct mutations resolving to state owned by an outer scope."""

        return self._python_facts.outer_state_mutations()

    def parameter_mutations(self) -> tuple[ParameterMutationFact, ...]:
        """Return first direct mutations of function parameters."""

        return self._python_facts.parameter_mutations()

    def project_calls(self) -> ProjectCallFacts:
        """Return project-resolvable discarded calls."""

        return self._python_facts.project_calls()

    def project_functions(self) -> tuple[ProjectFunctionFact, ...]:
        """Return top-level function result contracts."""

        return self._python_facts.project_functions()

    def references(self) -> ReferenceFacts:
        """Return import and attribute-reference facts."""

        return self._python_facts.references()

    def test_functions(self) -> tuple[PytestFunctionFact, ...]:
        """Return reusable syntax metadata for test functions."""

        return self._python_facts.test_functions()

    def top_level_definition_conditionals(self) -> tuple[SourceLocation, ...]:
        """Return test-policy conditionals owned by top-level definitions."""

        return self._python_facts.top_level_definition_conditionals()

    def test_module(self) -> PytestModuleFacts:
        """Return reusable test module-shape metadata."""

        return self._python_facts.test_module()
