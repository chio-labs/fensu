"""Python semantic-fact analysis implementation."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.annotations import annotation_facts
from strata.analysis.core.helpers.comments import comment_facts
from strata.analysis.core.helpers.control_flow import (
    complex_comprehension_locations,
    function_conditional_facts,
)
from strata.analysis.core.helpers.function_metrics import (
    dataclass_facts,
    function_facts,
    test_function_facts,
)
from strata.analysis.core.helpers.hygiene import hygiene_facts
from strata.analysis.core.helpers.locations import line_offsets, source_range
from strata.analysis.core.helpers.outer_state import (
    outer_state_mutation_nodes,
    parameter_mutation_facts,
)
from strata.analysis.core.helpers.references import reference_facts, test_module_facts
from strata.analysis.core.helpers.returns import meaningful_return_facts
from strata.analysis.core.models import (
    AnnotationFacts,
    CommentFact,
    DataclassFact,
    FunctionConditionalFact,
    FunctionFacts,
    HygieneFacts,
    MeaningfulReturnFact,
    OuterStateMutationFact,
    ParameterMutationFact,
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
        self._comments: tuple[CommentFact, ...] | None = None
        self._dataclasses: tuple[DataclassFact, ...] | None = None
        self._complex_comprehensions: tuple[SourceLocation, ...] | None = None
        self._function_conditionals: tuple[FunctionConditionalFact, ...] | None = None
        self._functions: FunctionFacts | None = None
        self._hygiene: HygieneFacts | None = None
        self._meaningful_returns: dict[tuple[str, ...], tuple[MeaningfulReturnFact, ...]] = {}
        self._outer_state_mutations: tuple[OuterStateMutationFact, ...] | None = None
        self._parameter_mutations: tuple[ParameterMutationFact, ...] | None = None
        self._references: ReferenceFacts | None = None
        self._test_functions: tuple[PytestFunctionFact, ...] | None = None
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

    def hygiene(self) -> HygieneFacts:
        """Return syntax-based hygiene facts."""

        if self._hygiene is None:
            self._hygiene = hygiene_facts(
                path=self._path,
                module=self._module,
                node_index=self._node_index,
            )
        return self._hygiene

    def meaningful_returns(
        self, *, name_patterns: tuple[str, ...] = ()
    ) -> tuple[MeaningfulReturnFact, ...]:
        """Return the first meaningful return owned by each function."""

        if name_patterns not in self._meaningful_returns:
            self._meaningful_returns[name_patterns] = meaningful_return_facts(
                path=self._path,
                node_index=self._node_index,
                name_patterns=name_patterns,
            )
        return self._meaningful_returns[name_patterns]

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
            )
        return self._test_functions

    def test_module(self) -> PytestModuleFacts:
        """Return reusable test module-shape metadata."""

        if self._test_module is None:
            self._test_module = test_module_facts(path=self._path, module=self._module)
        return self._test_module
