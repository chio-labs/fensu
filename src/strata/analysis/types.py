"""Private backend-neutral source-analysis contracts."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Protocol

if TYPE_CHECKING:
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
        ProjectDependency,
        ProjectFunctionFact,
        PytestFunctionFact,
        PytestModuleFacts,
        ReferenceFacts,
        SourceLocation,
        SourceRange,
        SyntaxHandle,
    )


class ProjectDependencyKind(StrEnum):
    """The project input observed by a cross-file query."""

    SOURCE = "source"
    EXISTS = "exists"
    IS_FILE = "is_file"
    IS_DIR = "is_dir"
    DIRECTORY_ENTRIES = "directory_entries"
    GLOB = "glob"
    PYTHON_ANCHOR = "python_anchor"


class ReturnAnnotationCategory(StrEnum):
    """Normalized return-annotation shapes used by contract policies."""

    MISSING = "missing"
    NONE = "none"
    BOOL = "bool"
    TYPE_GUARD = "type-guard"
    TYPE_IS = "type-is"
    ITERATOR = "iterator"
    GENERATOR = "generator"
    ASYNC_ITERATOR = "async-iterator"
    ASYNC_GENERATOR = "async-generator"
    OTHER = "other"


class RuleCaseForm(StrEnum):
    """The static shape supplying test_case to evaluate_rule."""

    MISSING = "missing"
    LITERAL = "literal"
    PARAMETER = "parameter"
    LOCAL = "local"
    DYNAMIC = "dynamic"


class TextAnalysis(Protocol):
    """Source text queries using backend-neutral locations."""

    @property
    def source(self) -> str:
        """Return the complete source text."""
        ...

    def line(self, line_number: int) -> str:
        """Return one source line without its line ending."""
        ...

    def slice(self, source_range: SourceRange) -> str:
        """Return the text covered by an end-exclusive source range."""
        ...


class SyntaxAnalysis(Protocol):
    """Backend-neutral syntax identity, kind, and location queries."""

    def handles(self, *, kind: str | None = None) -> tuple[SyntaxHandle, ...]:
        """Return syntax handles in deterministic traversal order."""
        ...

    def kind(self, handle: SyntaxHandle) -> str:
        """Return the Strata syntax kind for a handle."""
        ...

    def range(self, handle: SyntaxHandle) -> SourceRange:
        """Return the source range for a handle."""
        ...


class RelationAnalysis(Protocol):
    """Backend-neutral syntax relationship queries."""

    def parent(self, handle: SyntaxHandle) -> SyntaxHandle | None:
        """Return the direct parent handle, if present."""
        ...

    def children(self, handle: SyntaxHandle) -> tuple[SyntaxHandle, ...]:
        """Return direct child handles in source traversal order."""
        ...

    def ancestors(self, handle: SyntaxHandle) -> tuple[SyntaxHandle, ...]:
        """Return parents from nearest to farthest."""
        ...


class FactAnalysis(Protocol):
    """Backend-neutral semantic facts computed for the current file."""

    def annotations(self) -> AnnotationFacts:
        """Return missing function and local annotation facts."""
        ...

    def assignment_references(self) -> tuple[AssignmentReferenceFact, ...]:
        """Return assignments with lexical owners and strict RHS references."""
        ...

    def class_declarations(self) -> tuple[ClassDeclarationFact, ...]:
        """Return class declarations and direct methods in traversal order."""
        ...

    def comments(self) -> tuple[CommentFact, ...]:
        """Return source comments in token order."""
        ...

    def dataclasses(self) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass declarations and field metadata."""
        ...

    def evaluate_rule_calls(self) -> tuple[EvaluateRuleCallFact, ...]:
        """Return statically recognized public rule-harness calls."""
        ...

    def complex_comprehensions(self) -> tuple[SourceLocation, ...]:
        """Return complex comprehension locations."""
        ...

    def comparisons(self) -> tuple[ComparisonFact, ...]:
        """Return comparisons with position-aligned operand references."""
        ...

    def function_conditionals(self) -> tuple[FunctionConditionalFact, ...]:
        """Return conditional control flow grouped by owning function."""
        ...

    def functions(self) -> FunctionFacts:
        """Return reusable structural function metrics."""
        ...

    def function_contracts(self) -> tuple[FunctionContractFact, ...]:
        """Return descriptive name, annotation, yield, and return facts."""
        ...

    def hygiene(self) -> HygieneFacts:
        """Return syntax-based hygiene facts."""
        ...

    def meaningful_returns(
        self, *, name_patterns: tuple[str, ...] = ()
    ) -> tuple[MeaningfulReturnFact, ...]:
        """Return the first meaningful return owned by each function."""
        ...

    def local_call_edges(self) -> tuple[LocalCallEdgeFact, ...]:
        """Return calls attributed to every enclosing named function."""
        ...

    def module_declarations(self) -> ModuleDeclarationFacts:
        """Return module statements and classified declarations."""
        ...

    def named_calls(self) -> tuple[NamedCallFact, ...]:
        """Return all calls with nearest-first lexical owner chains."""
        ...

    def outer_state_mutations(self) -> tuple[OuterStateMutationFact, ...]:
        """Return direct mutations resolving to state owned by an outer scope."""
        ...

    def parameter_mutations(self) -> tuple[ParameterMutationFact, ...]:
        """Return first direct mutations of function parameters."""
        ...

    def parameter_mutation_occurrences(self) -> tuple[ParameterMutationOccurrenceFact, ...]:
        """Return every direct mutation occurrence of function parameters."""
        ...

    def project_calls(self) -> ProjectCallFacts:
        """Return project-resolvable discarded calls."""
        ...

    def project_functions(self) -> tuple[ProjectFunctionFact, ...]:
        """Return top-level function result contracts."""
        ...

    def references(self) -> ReferenceFacts:
        """Return import and attribute-reference facts."""
        ...

    def test_functions(self) -> tuple[PytestFunctionFact, ...]:
        """Return reusable syntax metadata for test functions."""
        ...

    def top_level_definition_conditionals(self) -> tuple[SourceLocation, ...]:
        """Return test-policy conditionals owned by top-level definitions."""
        ...

    def test_module(self) -> PytestModuleFacts:
        """Return reusable test module-shape metadata."""
        ...


class Analysis(Protocol):
    """Private replaceable analysis facade attached to a rule context."""

    @property
    def text(self) -> TextAnalysis:
        """Return source-text queries."""
        ...

    @property
    def syntax(self) -> SyntaxAnalysis:
        """Return syntax queries."""
        ...

    @property
    def relations(self) -> RelationAnalysis:
        """Return syntax-relation queries."""
        ...

    @property
    def facts(self) -> FactAnalysis:
        """Return semantic file facts."""
        ...


class ProjectAnalysis(Protocol):
    """Backend-neutral cross-file analysis and filesystem queries."""

    def analysis(self, *, requester: Path, path: Path) -> Analysis | None:
        """Return analysis for a project path and record the dependency."""
        ...

    def dependencies(self) -> tuple[ProjectDependency, ...]:
        """Return deterministic requester-to-path dependencies observed so far."""
        ...

    def dependencies_for(self, *, requester: Path) -> tuple[ProjectDependency, ...]:
        """Return deterministic dependencies observed for one requester."""
        ...

    def dataclasses(self, *, requester: Path, path: Path) -> tuple[DataclassFact, ...]:
        """Return top-level dataclass facts for a project path."""
        ...

    def directory_entries(self, *, requester: Path, path: Path) -> tuple[Path, ...]:
        """Return direct children and record a directory namespace dependency."""
        ...

    def module_function(
        self, *, requester: Path, module_name: str, function_name: str
    ) -> ProjectFunctionFact | None:
        """Return a function contract from a resolvable project module."""
        ...

    def entrypoint_modules(self, *, requester: Path) -> tuple[str, ...]:
        """Return modules referenced by standardized project entrypoint declarations."""
        ...

    def python_anchor(self, *, requester: Path, path: Path) -> Path | None:
        """Return the deterministic Python ownership anchor for a package directory."""
        ...

    def exists(self, *, requester: Path, path: Path) -> bool:
        """Return whether a project path exists and record the dependency."""
        ...

    def is_dir(self, *, requester: Path, path: Path) -> bool:
        """Return whether a project path is a directory and record the dependency."""
        ...

    def is_file(self, *, requester: Path, path: Path) -> bool:
        """Return whether a project path is a file and record the dependency."""
        ...

    def glob(
        self,
        *,
        requester: Path,
        path: Path,
        pattern: str,
        recursive: bool = False,
    ) -> tuple[Path, ...]:
        """Return direct or recursive path matches and record an aggregate dependency."""
        ...


class SyntaxIndexes(NamedTuple):
    """One breadth-first node tuple plus its compatibility indexes."""

    nodes: tuple[ast.AST, ...]
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]]
    parent_by_node: Mapping[ast.AST, ast.AST]


class PythonSourceArtifact(NamedTuple):
    """One exact decoded and parsed Python source snapshot."""

    path: Path
    source: str
    source_fingerprint: str
    module: ast.Module
