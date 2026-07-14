"""Native-backend fact facade delegating unported families to Python."""

from __future__ import annotations

import sys
from fnmatch import fnmatchcase
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.models import MeaningfulReturnFact
from strata.instrumentation.constants import NATIVE_PARSE_OPERATION, OPERATION_COUNTERS

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from strata.analysis.models import (
        AnnotationFacts,
        CommentFact,
        DataclassFact,
        EvaluateRuleCallFact,
        FunctionConditionalFact,
        FunctionContractFact,
        FunctionFacts,
        HygieneFacts,
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

    _ControlFlowFacts = tuple[
        tuple[FunctionConditionalFact, ...],
        tuple[SourceLocation, ...],
        tuple[SourceLocation, ...],
    ]
    _ProjectFacts = tuple[tuple[ProjectFunctionFact, ...], ProjectCallFacts]


class NativeFactAnalysis:
    """Semantic file facts served natively, family by family, as ports land."""

    def __init__(
        self,
        *,
        python_facts: Callable[[], FactAnalysis],
        path: Path,
        source: str,
        program: object | None = None,
    ) -> None:
        """Bind the lazy Python fallback and adopt any pre-parsed native program."""

        self._python_facts: Callable[[], FactAnalysis] = python_facts
        self._fallback: FactAnalysis | None = None
        self._path: Path = path
        self._source: str = source
        self._native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
        self._program: object | None = program
        self._program_failed: bool = False
        self._annotations: AnnotationFacts | None = None
        self._comments: tuple[CommentFact, ...] | None = None
        self._function_contracts: tuple[FunctionContractFact, ...] | None = None
        self._functions: FunctionFacts | None = None
        self._parameter_mutations: tuple[ParameterMutationFact, ...] | None = None
        self._meaningful_returns: dict[tuple[str, ...], tuple[MeaningfulReturnFact, ...]] = {}
        self._module_declarations: ModuleDeclarationFacts | None = None
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
            program: object | None = self._parsed_program()
            self._annotations = (
                self._fallback_facts().annotations()
                if program is None
                else self._native.annotation_facts(program, self._path)
            )
        return self._annotations

    def comments(self) -> tuple[CommentFact, ...]:
        """Return source comments in token order."""

        if self._comments is None:
            program: object | None = self._parsed_program()
            self._comments = (
                self._fallback_facts().comments()
                if program is None
                else self._native.comment_facts(program, self._path)
            )
        return self._comments

    def _resolved_project_facts(self) -> _ProjectFacts | None:
        if self._project_facts is None:
            program: object | None = self._parsed_program()
            if program is None:
                return None
            self._project_facts = self._native.project_facts(program, self._path)
        return self._project_facts

    def _control_flow_facts(self) -> _ControlFlowFacts | None:
        if self._control_flow is None:
            program: object | None = self._parsed_program()
            if program is None:
                return None
            self._control_flow = self._native.control_flow_facts(program, self._path)
        return self._control_flow

    def _parsed_program(self) -> object | None:
        if self._program is None and not self._program_failed:
            OPERATION_COUNTERS.record(operation=NATIVE_PARSE_OPERATION)
            try:
                self._program = self._native.parse_program(
                    self._source,
                    sys.version_info[0],
                    sys.version_info[1],
                )
            except ValueError:
                self._program_failed = True
        return self._program

    def _fallback_facts(self) -> FactAnalysis:
        if self._fallback is None:
            self._fallback = self._python_facts()
        return self._fallback

    def dataclasses(self) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass declarations and field metadata."""

        if self._dataclasses is None:
            program: object | None = self._parsed_program()
            self._dataclasses = (
                self._fallback_facts().dataclasses()
                if program is None
                else self._native.dataclass_facts(program, self._path)
            )
        return self._dataclasses

    def evaluate_rule_calls(self) -> tuple[EvaluateRuleCallFact, ...]:
        """Return statically recognized public rule-harness calls."""

        if self._evaluate_rule_calls is None:
            program: object | None = self._parsed_program()
            self._evaluate_rule_calls = (
                self._fallback_facts().evaluate_rule_calls()
                if program is None
                else self._native.evaluate_rule_call_facts(program, self._path)
            )
        return self._evaluate_rule_calls

    def complex_comprehensions(self) -> tuple[SourceLocation, ...]:
        """Return complex comprehension locations."""

        control_flow: _ControlFlowFacts | None = self._control_flow_facts()
        if control_flow is None:
            return self._fallback_facts().complex_comprehensions()
        return control_flow[1]

    def function_conditionals(self) -> tuple[FunctionConditionalFact, ...]:
        """Return conditional control flow grouped by owning function."""

        control_flow: _ControlFlowFacts | None = self._control_flow_facts()
        if control_flow is None:
            return self._fallback_facts().function_conditionals()
        return control_flow[0]

    def functions(self) -> FunctionFacts:
        """Return reusable structural function metrics."""

        if self._functions is None:
            program: object | None = self._parsed_program()
            self._functions = (
                self._fallback_facts().functions()
                if program is None
                else self._native.function_facts(program, self._path)
            )
        return self._functions

    def function_contracts(self) -> tuple[FunctionContractFact, ...]:
        """Return descriptive name, annotation, yield, and return facts."""

        if self._function_contracts is None:
            program: object | None = self._parsed_program()
            native_facts: tuple[FunctionContractFact, ...] | None = (
                None
                if program is None
                else self._native.function_contract_facts(program, self._path)
            )
            self._function_contracts = (
                self._fallback_facts().function_contracts()
                if native_facts is None
                else native_facts
            )
        return self._function_contracts

    def hygiene(self) -> HygieneFacts:
        """Return syntax-based hygiene facts."""

        if self._hygiene is None:
            program: object | None = self._parsed_program()
            self._hygiene = (
                self._fallback_facts().hygiene()
                if program is None
                else self._native.hygiene_facts(program, self._path)
            )
        return self._hygiene

    def meaningful_returns(
        self, *, name_patterns: tuple[str, ...] = ()
    ) -> tuple[MeaningfulReturnFact, ...]:
        """Return the first meaningful return owned by each function."""

        if name_patterns not in self._meaningful_returns:
            if self._parsed_program() is None:
                return self._fallback_facts().meaningful_returns(name_patterns=name_patterns)
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
            program: object | None = self._parsed_program()
            self._module_declarations = (
                self._fallback_facts().module_declarations()
                if program is None
                else self._native.module_declaration_facts(program, self._path)
            )
        return self._module_declarations

    def outer_state_mutations(self) -> tuple[OuterStateMutationFact, ...]:
        """Return direct mutations resolving to state owned by an outer scope."""

        if self._outer_state_mutations is None:
            program: object | None = self._parsed_program()
            self._outer_state_mutations = (
                self._fallback_facts().outer_state_mutations()
                if program is None
                else self._native.outer_state_mutation_facts(program, self._path)
            )
        return self._outer_state_mutations

    def parameter_mutations(self) -> tuple[ParameterMutationFact, ...]:
        """Return first direct mutations of function parameters."""

        if self._parameter_mutations is None:
            program: object | None = self._parsed_program()
            self._parameter_mutations = (
                self._fallback_facts().parameter_mutations()
                if program is None
                else self._native.parameter_mutation_facts(program, self._path)
            )
        return self._parameter_mutations

    def project_calls(self) -> ProjectCallFacts:
        """Return project-resolvable discarded calls."""

        project_facts: _ProjectFacts | None = self._resolved_project_facts()
        if project_facts is None:
            return self._fallback_facts().project_calls()
        return project_facts[1]

    def project_functions(self) -> tuple[ProjectFunctionFact, ...]:
        """Return top-level function result contracts."""

        project_facts: _ProjectFacts | None = self._resolved_project_facts()
        if project_facts is None:
            return self._fallback_facts().project_functions()
        return project_facts[0]

    def references(self) -> ReferenceFacts:
        """Return import and attribute-reference facts."""

        if self._references is None:
            program: object | None = self._parsed_program()
            self._references = (
                self._fallback_facts().references()
                if program is None
                else self._native.reference_facts(program, self._path)
            )
        return self._references

    def test_functions(self) -> tuple[PytestFunctionFact, ...]:
        """Return reusable syntax metadata for test functions."""

        if self._test_functions is None:
            program: object | None = self._parsed_program()
            self._test_functions = (
                self._fallback_facts().test_functions()
                if program is None
                else self._native.test_function_facts(program, self._path)
            )
        return self._test_functions

    def top_level_definition_conditionals(self) -> tuple[SourceLocation, ...]:
        """Return test-policy conditionals owned by top-level definitions."""

        control_flow: _ControlFlowFacts | None = self._control_flow_facts()
        if control_flow is None:
            return self._fallback_facts().top_level_definition_conditionals()
        return control_flow[2]

    def test_module(self) -> PytestModuleFacts:
        """Return reusable test module-shape metadata."""

        if self._test_module is None:
            program: object | None = self._parsed_program()
            self._test_module = (
                self._fallback_facts().test_module()
                if program is None
                else self._native.test_module_facts(program, self._path)
            )
        return self._test_module
