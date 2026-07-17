"""Semantic fact facade backed exclusively by the native program."""

from __future__ import annotations

import sys
from fnmatch import fnmatchcase
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.exceptions import NativeSourceCompatibilityError
from strata.analysis.models import MeaningfulReturnFact
from strata.instrumentation.constants import NATIVE_PARSE_OPERATION, OPERATION_COUNTERS

if TYPE_CHECKING:
    from pathlib import Path

    from strata.analysis.models import (
        AnnotationFacts,
        AssignmentReferenceFact,
        ClassDeclarationFact,
        CommentFact,
        ComparisonFact,
        DataclassFact,
        EvaluateRuleCallFact,
        FunctionConditionalFact,
        FunctionContractFact,
        FunctionFacts,
        HygieneFacts,
        LocalCallEdgeFact,
        ModuleDeclarationFacts,
        NamedCallFact,
        OuterStateMutationFact,
        ParameterMutationFact,
        ParameterMutationOccurrenceFact,
        ProjectCallFacts,
        ProjectFunctionFact,
        PytestFunctionFact,
        PytestModuleFacts,
        ReferenceFacts,
        SourceLocation,
    )

    _ControlFlowFacts = tuple[
        tuple[FunctionConditionalFact, ...],
        tuple[SourceLocation, ...],
        tuple[SourceLocation, ...],
    ]
    _ProjectFacts = tuple[tuple[ProjectFunctionFact, ...], ProjectCallFacts]


class SemanticFactAnalysis:
    """Semantic file facts served exclusively by the native extension."""

    def __init__(
        self,
        *,
        path: Path,
        source: str,
        program: object | None = None,
    ) -> None:
        """Bind source identity and adopt any pre-parsed native program."""

        self._path: Path = path
        self._source: str = source
        self._native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
        self._program: object | None = program
        self._annotations: AnnotationFacts | None = None
        self._assignment_references: tuple[AssignmentReferenceFact, ...] | None = None
        self._class_declarations: tuple[ClassDeclarationFact, ...] | None = None
        self._comments: tuple[CommentFact, ...] | None = None
        self._comparisons: tuple[ComparisonFact, ...] | None = None
        self._function_contracts: tuple[FunctionContractFact, ...] | None = None
        self._functions: FunctionFacts | None = None
        self._parameter_mutations: tuple[ParameterMutationFact, ...] | None = None
        self._parameter_mutation_occurrences: tuple[ParameterMutationOccurrenceFact, ...] | None = (
            None
        )
        self._meaningful_returns: dict[tuple[str, ...], tuple[MeaningfulReturnFact, ...]] = {}
        self._local_call_edges: tuple[LocalCallEdgeFact, ...] | None = None
        self._module_declarations: ModuleDeclarationFacts | None = None
        self._named_calls: tuple[NamedCallFact, ...] | None = None
        self._outer_state_mutations: tuple[OuterStateMutationFact, ...] | None = None
        self._dataclasses: tuple[DataclassFact, ...] | None = None
        self._project_facts: tuple[tuple[ProjectFunctionFact, ...], ProjectCallFacts] | None = None
        self._references: ReferenceFacts | None = None
        self._test_module: PytestModuleFacts | None = None
        self._test_functions: tuple[PytestFunctionFact, ...] | None = None
        self._evaluate_rule_calls: tuple[EvaluateRuleCallFact, ...] | None = None
        self._hygiene: HygieneFacts | None = None
        self._control_flow: (
            tuple[
                tuple[FunctionConditionalFact, ...],
                tuple[SourceLocation, ...],
                tuple[SourceLocation, ...],
            ]
            | None
        ) = None

    def annotations(self) -> AnnotationFacts:
        """Return missing function and local annotation facts."""

        if self._annotations is None:
            self._annotations = self._native.annotation_facts(self._parsed_program(), self._path)
        return self._annotations

    def assignment_references(self) -> tuple[AssignmentReferenceFact, ...]:
        """Return assignments with lexical owners and strict RHS references."""

        if self._assignment_references is None:
            self._assignment_references = self._native.assignment_reference_facts(
                self._parsed_program(), self._path
            )
        return self._assignment_references

    def class_declarations(self) -> tuple[ClassDeclarationFact, ...]:
        """Return class declarations and direct methods in traversal order."""

        if self._class_declarations is None:
            self._class_declarations = self._native.class_declaration_facts(
                self._parsed_program(), self._path
            )
        return self._class_declarations

    def comments(self) -> tuple[CommentFact, ...]:
        """Return source comments in token order."""

        if self._comments is None:
            self._comments = self._native.comment_facts(self._parsed_program(), self._path)
        return self._comments

    def _resolved_project_facts(self) -> _ProjectFacts:
        if self._project_facts is None:
            program: object = self._parsed_program()
            self._project_facts = self._native.project_facts(program, self._path)
        return self._project_facts

    def _control_flow_facts(self) -> _ControlFlowFacts:
        if self._control_flow is None:
            program: object = self._parsed_program()
            self._control_flow = self._native.control_flow_facts(program, self._path)
        return self._control_flow

    def _parsed_program(self) -> object:
        if self._program is None:
            OPERATION_COUNTERS.record(operation=NATIVE_PARSE_OPERATION)
            try:
                self._program = self._native.parse_program(
                    self._source,
                    sys.version_info[0],
                    sys.version_info[1],
                )
            except ValueError as error:
                raise NativeSourceCompatibilityError(
                    path=self._path,
                    detail=str(error),
                ) from error
        return self._program

    def dataclasses(self) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass declarations and field metadata."""

        if self._dataclasses is None:
            self._dataclasses = self._native.dataclass_facts(self._parsed_program(), self._path)
        return self._dataclasses

    def evaluate_rule_calls(self) -> tuple[EvaluateRuleCallFact, ...]:
        """Return statically recognized public rule-harness calls."""

        if self._evaluate_rule_calls is None:
            self._evaluate_rule_calls = self._native.evaluate_rule_call_facts(
                self._parsed_program(), self._path
            )
        return self._evaluate_rule_calls

    def complex_comprehensions(self) -> tuple[SourceLocation, ...]:
        """Return complex comprehension locations."""

        return self._control_flow_facts()[1]

    def comparisons(self) -> tuple[ComparisonFact, ...]:
        """Return comparisons with position-aligned operand references."""

        if self._comparisons is None:
            self._comparisons = self._native.comparison_facts(self._parsed_program(), self._path)
        return self._comparisons

    def function_conditionals(self) -> tuple[FunctionConditionalFact, ...]:
        """Return conditional control flow grouped by owning function."""

        return self._control_flow_facts()[0]

    def functions(self) -> FunctionFacts:
        """Return reusable structural function metrics."""

        if self._functions is None:
            self._functions = self._native.function_facts(self._parsed_program(), self._path)
        return self._functions

    def function_contracts(self) -> tuple[FunctionContractFact, ...]:
        """Return descriptive name, annotation, yield, and return facts."""

        if self._function_contracts is None:
            self._function_contracts = self._native.function_contract_facts(
                self._parsed_program(), self._path
            )
        return self._function_contracts

    def hygiene(self) -> HygieneFacts:
        """Return syntax-based hygiene facts."""

        if self._hygiene is None:
            self._hygiene = self._native.hygiene_facts(self._parsed_program(), self._path)
        return self._hygiene

    def meaningful_returns(
        self, *, name_patterns: tuple[str, ...] = ()
    ) -> tuple[MeaningfulReturnFact, ...]:
        """Return the first meaningful return owned by each function."""

        if name_patterns not in self._meaningful_returns:
            facts: list[MeaningfulReturnFact] = []
            for fact in self.function_contracts():
                location: SourceLocation | None = fact.meaningful_return_location
                matches: bool = not name_patterns or any(
                    fnmatchcase(fact.function_name, pattern) for pattern in name_patterns
                )
                if location is not None and matches:
                    facts.append(
                        MeaningfulReturnFact(
                            function_name=fact.function_name,
                            location=location,
                        )
                    )
            self._meaningful_returns[name_patterns] = tuple(facts)
        return self._meaningful_returns[name_patterns]

    def module_declarations(self) -> ModuleDeclarationFacts:
        """Return module statements and classified declarations."""

        if self._module_declarations is None:
            self._module_declarations = self._native.module_declaration_facts(
                self._parsed_program(), self._path
            )
        return self._module_declarations

    def local_call_edges(self) -> tuple[LocalCallEdgeFact, ...]:
        """Return calls attributed to every enclosing named function."""

        if self._local_call_edges is None:
            self._local_call_edges = self._native.local_call_edge_facts(
                self._parsed_program(), self._path
            )
        return self._local_call_edges

    def named_calls(self) -> tuple[NamedCallFact, ...]:
        """Return all calls with nearest-first lexical owner chains."""

        if self._named_calls is None:
            self._named_calls = self._native.named_call_facts(self._parsed_program(), self._path)
        return self._named_calls

    def outer_state_mutations(self) -> tuple[OuterStateMutationFact, ...]:
        """Return direct mutations resolving to state owned by an outer scope."""

        if self._outer_state_mutations is None:
            self._outer_state_mutations = self._native.outer_state_mutation_facts(
                self._parsed_program(), self._path
            )
        return self._outer_state_mutations

    def parameter_mutations(self) -> tuple[ParameterMutationFact, ...]:
        """Return first direct mutations of function parameters."""

        if self._parameter_mutations is None:
            self._parameter_mutations = self._native.parameter_mutation_facts(
                self._parsed_program(), self._path
            )
        return self._parameter_mutations

    def parameter_mutation_occurrences(self) -> tuple[ParameterMutationOccurrenceFact, ...]:
        """Return every direct mutation occurrence of function parameters."""

        if self._parameter_mutation_occurrences is None:
            self._parameter_mutation_occurrences = self._native.parameter_mutation_occurrence_facts(
                self._parsed_program(), self._path
            )
        return self._parameter_mutation_occurrences

    def project_calls(self) -> ProjectCallFacts:
        """Return project-resolvable discarded calls."""

        return self._resolved_project_facts()[1]

    def project_functions(self) -> tuple[ProjectFunctionFact, ...]:
        """Return top-level function result contracts."""

        return self._resolved_project_facts()[0]

    def references(self) -> ReferenceFacts:
        """Return import and attribute-reference facts."""

        if self._references is None:
            self._references = self._native.reference_facts(self._parsed_program(), self._path)
        return self._references

    def test_functions(self) -> tuple[PytestFunctionFact, ...]:
        """Return reusable syntax metadata for test functions."""

        if self._test_functions is None:
            self._test_functions = self._native.test_function_facts(
                self._parsed_program(), self._path
            )
        return self._test_functions

    def top_level_definition_conditionals(self) -> tuple[SourceLocation, ...]:
        """Return test-policy conditionals owned by top-level definitions."""

        return self._control_flow_facts()[2]

    def test_module(self) -> PytestModuleFacts:
        """Return reusable test module-shape metadata."""

        if self._test_module is None:
            self._test_module = self._native.test_module_facts(self._parsed_program(), self._path)
        return self._test_module
