"""Python semantic-fact analysis implementation."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import Path

from strata.analysis._helpers.annotations import annotation_facts
from strata.analysis._helpers.control_flow import (
    complex_comprehension_locations,
    function_conditional_facts,
    test_conditional_locations,
)
from strata.analysis._helpers.declarations import class_declaration_facts, module_declaration_facts
from strata.analysis._helpers.function_metrics import (
    dataclass_facts,
    function_facts,
    test_function_facts,
)
from strata.analysis._helpers.hygiene import comment_facts, hygiene_facts
from strata.analysis._helpers.locations import line_offsets, source_range
from strata.analysis._helpers.outer_state import (
    outer_state_mutation_nodes,
    parameter_mutation_facts,
    parameter_mutation_occurrence_facts,
)
from strata.analysis._helpers.references import (
    assignment_reference_facts,
    comparison_facts,
    local_call_edge_facts,
    named_call_facts,
    reference_facts,
    test_module_facts,
)
from strata.analysis._helpers.returns import (
    function_contract_facts,
    project_call_facts,
    project_function_facts,
)
from strata.analysis.classes.harness_use_extractor import HarnessUseExtractor
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
    MeaningfulReturnFact,
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


class PythonFactAnalysis:
    """Lazy semantic facts backed by shared Python AST indexes."""

    def __init__(
        self,
        *,
        path: Path,
        source: str,
        module: ast.Module,
        nodes: tuple[ast.AST, ...],
        node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
        parent_by_node: Mapping[ast.AST, ast.AST],
    ) -> None:
        """Bind shared syntax indexes without computing semantic facts."""

        self._path: Path = path
        self._source: str = source
        self._module: ast.Module = module
        self._nodes: tuple[ast.AST, ...] = nodes
        self._node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]] = node_index
        self._parent_by_node: Mapping[ast.AST, ast.AST] = parent_by_node
        self._annotations: AnnotationFacts | None = None
        self._assignment_references: tuple[AssignmentReferenceFact, ...] | None = None
        self._class_declarations: tuple[ClassDeclarationFact, ...] | None = None
        self._comments: tuple[CommentFact, ...] | None = None
        self._comparisons: tuple[ComparisonFact, ...] | None = None
        self._dataclasses: tuple[DataclassFact, ...] | None = None
        self._complex_comprehensions: tuple[SourceLocation, ...] | None = None
        self._function_conditionals: tuple[FunctionConditionalFact, ...] | None = None
        self._function_contracts: tuple[FunctionContractFact, ...] | None = None
        self._functions: FunctionFacts | None = None
        self._hygiene: HygieneFacts | None = None
        self._harness_use_extractor: HarnessUseExtractor | None = None
        self._meaningful_returns: dict[tuple[str, ...], tuple[MeaningfulReturnFact, ...]] = {}
        self._local_call_edges: tuple[LocalCallEdgeFact, ...] | None = None
        self._module_declarations: ModuleDeclarationFacts | None = None
        self._named_calls: tuple[NamedCallFact, ...] | None = None
        self._outer_state_mutations: tuple[OuterStateMutationFact, ...] | None = None
        self._parameter_mutations: tuple[ParameterMutationFact, ...] | None = None
        self._parameter_mutation_occurrences: tuple[ParameterMutationOccurrenceFact, ...] | None = (
            None
        )
        self._project_calls: ProjectCallFacts | None = None
        self._project_functions: tuple[ProjectFunctionFact, ...] | None = None
        self._references: ReferenceFacts | None = None
        self._test_functions: tuple[PytestFunctionFact, ...] | None = None
        self._top_level_definition_conditionals: tuple[SourceLocation, ...] | None = None
        self._test_module: PytestModuleFacts | None = None

    def annotations(self) -> AnnotationFacts:
        """Return missing annotations from one shared traversal."""

        if self._annotations is None:
            self._annotations = annotation_facts(
                path=self._path,
                module=self._module,
                node_index=self._node_index,
            )
        return self._annotations

    def assignment_references(self) -> tuple[AssignmentReferenceFact, ...]:
        """Return assignments with lexical owners and strict RHS references."""

        if self._assignment_references is None:
            self._assignment_references = assignment_reference_facts(
                path=self._path,
                nodes=self._nodes,
                parent_by_node=self._parent_by_node,
            )
        return self._assignment_references

    def class_declarations(self) -> tuple[ClassDeclarationFact, ...]:
        """Return class declarations and direct methods in traversal order."""

        if self._class_declarations is None:
            self._class_declarations = class_declaration_facts(
                path=self._path,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
        return self._class_declarations

    def comments(self) -> tuple[CommentFact, ...]:
        """Return source comments in token order."""

        if self._comments is None:
            self._comments = comment_facts(path=self._path, source=self._source)
        return self._comments

    def dataclasses(self) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass declarations and field metadata."""

        if self._dataclasses is None:
            self._dataclasses = dataclass_facts(path=self._path, module=self._module)
        return self._dataclasses

    def complex_comprehensions(self) -> tuple[SourceLocation, ...]:
        """Return complex comprehension locations."""

        if self._complex_comprehensions is None:
            self._complex_comprehensions = complex_comprehension_locations(
                path=self._path,
                node_index=self._node_index,
            )
        return self._complex_comprehensions

    def comparisons(self) -> tuple[ComparisonFact, ...]:
        """Return comparisons with position-aligned operand references."""

        if self._comparisons is None:
            self._comparisons = comparison_facts(path=self._path, nodes=self._nodes)
        return self._comparisons

    def outer_state_mutations(self) -> tuple[OuterStateMutationFact, ...]:
        """Return direct mutations resolving to state owned by an outer scope."""

        if self._outer_state_mutations is None:
            mutation_nodes: tuple[ast.AST, ...] = outer_state_mutation_nodes(
                module=self._module,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
            if not mutation_nodes:
                self._outer_state_mutations = ()
                return self._outer_state_mutations
            offsets: tuple[int, ...] = line_offsets(self._source)
            self._outer_state_mutations = tuple(
                OuterStateMutationFact(
                    location=source_range(
                        path=self._path,
                        source=self._source,
                        line_offsets=offsets,
                        node=node,
                    )
                )
                for node in mutation_nodes
            )
        return self._outer_state_mutations

    def function_conditionals(self) -> tuple[FunctionConditionalFact, ...]:
        """Return conditional control flow grouped by owning function."""

        if self._function_conditionals is None:
            self._function_conditionals = function_conditional_facts(
                path=self._path,
                source=self._source,
                node_index=self._node_index,
            )
        return self._function_conditionals

    def parameter_mutations(self) -> tuple[ParameterMutationFact, ...]:
        """Return first direct mutations of function parameters."""

        if self._parameter_mutations is None:
            self._parameter_mutations = parameter_mutation_facts(
                path=self._path,
                nodes=self._nodes,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
        return self._parameter_mutations

    def parameter_mutation_occurrences(self) -> tuple[ParameterMutationOccurrenceFact, ...]:
        """Return every direct mutation occurrence of function parameters."""

        if self._parameter_mutation_occurrences is None:
            self._parameter_mutation_occurrences = parameter_mutation_occurrence_facts(
                path=self._path,
                nodes=self._nodes,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
        return self._parameter_mutation_occurrences

    def project_calls(self) -> ProjectCallFacts:
        """Return project-resolvable discarded calls."""

        if self._project_calls is None:
            self._project_calls = project_call_facts(path=self._path, module=self._module)
        return self._project_calls

    def project_functions(self) -> tuple[ProjectFunctionFact, ...]:
        """Return top-level function result contracts."""

        if self._project_functions is None:
            self._project_functions = project_function_facts(module=self._module)
        return self._project_functions

    def functions(self) -> FunctionFacts:
        """Return reusable structural function metrics."""

        if self._functions is None:
            self._functions = function_facts(
                path=self._path,
                module=self._module,
                nodes=self._nodes,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
        return self._functions

    def function_contracts(self) -> tuple[FunctionContractFact, ...]:
        """Return descriptive function contract facts."""

        if self._function_contracts is None:
            self._function_contracts = function_contract_facts(
                path=self._path,
                node_index=self._node_index,
            )
        return self._function_contracts

    def hygiene(self) -> HygieneFacts:
        """Return syntax-based hygiene facts."""

        if self._hygiene is None:
            self._hygiene = hygiene_facts(
                path=self._path,
                module=self._module,
                node_index=self._node_index,
            )
        return self._hygiene

    def evaluate_rule_calls(self) -> tuple[EvaluateRuleCallFact, ...]:
        """Return statically recognized public rule-harness calls."""

        return self._harness_uses().evaluate_rule_calls()

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
            self._module_declarations = module_declaration_facts(
                path=self._path,
                module=self._module,
                node_index=self._node_index,
            )
        return self._module_declarations

    def local_call_edges(self) -> tuple[LocalCallEdgeFact, ...]:
        """Return calls attributed to every enclosing named function."""

        if self._local_call_edges is None:
            self._local_call_edges = local_call_edge_facts(
                path=self._path,
                nodes=self._nodes,
                parent_by_node=self._parent_by_node,
            )
        return self._local_call_edges

    def named_calls(self) -> tuple[NamedCallFact, ...]:
        """Return all calls with nearest-first lexical owner chains."""

        if self._named_calls is None:
            self._named_calls = named_call_facts(
                path=self._path,
                nodes=self._nodes,
                parent_by_node=self._parent_by_node,
            )
        return self._named_calls

    def references(self) -> ReferenceFacts:
        """Return import and attribute-reference facts."""

        if self._references is None:
            self._references = reference_facts(
                path=self._path,
                module=self._module,
                nodes=self._nodes,
                node_index=self._node_index,
            )
        return self._references

    def test_functions(self) -> tuple[PytestFunctionFact, ...]:
        """Return reusable syntax metadata for test functions."""

        if self._test_functions is None:
            self._test_functions = test_function_facts(
                path=self._path,
                node_index=self._node_index,
                dimensions_by_function=self._harness_uses().parametrize_dimensions(),
            )
        return self._test_functions

    def _harness_uses(self) -> HarnessUseExtractor:
        if self._harness_use_extractor is None:
            self._harness_use_extractor = HarnessUseExtractor(
                path=self._path,
                module=self._module,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
        return self._harness_use_extractor

    def top_level_definition_conditionals(self) -> tuple[SourceLocation, ...]:
        """Return test-policy conditionals owned by top-level definitions."""

        if self._top_level_definition_conditionals is None:
            definitions: tuple[ast.AST, ...] = tuple(
                statement
                for statement in self._module.body
                if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            )
            self._top_level_definition_conditionals = test_conditional_locations(
                path=self._path,
                definitions=definitions,
            )
        return self._top_level_definition_conditionals

    def test_module(self) -> PytestModuleFacts:
        """Return reusable test module-shape metadata."""

        if self._test_module is None:
            self._test_module = test_module_facts(path=self._path, module=self._module)
        return self._test_module
