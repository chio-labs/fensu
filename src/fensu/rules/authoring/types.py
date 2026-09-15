"""Authoring type-layer declarations: taxonomy, thresholds, and the check contract."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from fensu.discovery.types import ScopeName

if TYPE_CHECKING:
    from fensu.analysis.models import (
        DataclassFact,
        ProjectDependency,
        ProjectFunctionFact,
        SourceLocation,
        SourceRange,
        SyntaxHandle,
    )
    from fensu.analysis.types import (
        Analysis,
        FactAnalysis,
        RelationAnalysis,
        SyntaxAnalysis,
        TextAnalysis,
    )
    from fensu.rules.authoring.models import (
        ArchitectureGraph,
        CustomRuleRegistration,
        Fault,
        ProjectPath,
        ProjectTree,
        RuleOption,
        RustWorkspaceFacts,
    )

type RuleOptionValue = bool | int | str | tuple[str, ...] | tuple[int, ...]


class SourceKind(StrEnum):
    """Analyzer-neutral source representation identity."""

    PYTHON_MODULE = "python_module"
    RUST_MODULE = "rust_module"


class ImportResolution(StrEnum):
    """Whether a static import resolves to a discovered project module."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class ModuleVisibility(StrEnum):
    """Structural visibility exposed by a discovered module."""

    PUBLIC = "public"
    INTERNAL = "internal"


class RustItemKind(StrEnum):
    """Fensu-owned Rust declaration categories."""

    FUNCTION = "function"
    STRUCT = "struct"
    ENUM = "enum"
    TRAIT = "trait"
    IMPLEMENTATION = "implementation"
    MODULE = "module"


class RustVisibility(StrEnum):
    """Normalized Rust declaration visibility."""

    PUBLIC = "public"
    CRATE = "crate"
    RESTRICTED = "restricted"
    PRIVATE = "private"


class RustUseResolution(StrEnum):
    """Strongest statically provable destination of an authored Rust use path."""

    RESOLVED = "resolved"
    CRATE = "crate"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


class Family(StrEnum):
    """The rule family a rule belongs to."""

    LAYERS = "layers"
    ROLES = "roles"
    SHAPE = "shape"
    NAMING = "naming"
    HYGIENE = "hygiene"
    TESTS = "tests"
    ANNOTATIONS = "annotations"
    CONTRACTS = "contracts"
    PARSING = "parsing"
    CUSTOM = "custom"


class Severity(StrEnum):
    """The severity assigned to a fault."""

    ERROR = "error"
    WARNING = "warning"


class RuleKind(StrEnum):
    """Whether a rule ships with fensu or is authored downstream."""

    CORE = "core"
    PACK = "pack"
    CUSTOM = "custom"


class ExecutionOwner(StrEnum):
    """The repository owner that receives one rule invocation."""

    FILE = "file"
    PACKAGE = "package"
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    LEAF = "leaf"
    SCOPE = "scope"
    PROJECT = "project"


class RuleSubjectKind(StrEnum):
    """The callback shape used to invoke a Python-authored rule."""

    LEGACY = "legacy"
    FILE = "file"
    PROJECT = "project"


class RuleOptionKind(StrEnum):
    """The canonical scalar or immutable-list shape of one rule option."""

    BOOLEAN = "boolean"
    INTEGER = "integer"
    STRING = "string"
    STRING_LIST = "string_list"
    INTEGER_LIST = "integer_list"


class Missing(StrEnum):
    """Sentinel type distinguishing an omitted option default from falsey values."""

    VALUE = "missing"


class Threshold(StrEnum):
    """Named, config-overridable numeric limits resolved per reported path."""

    MAX_STATEMENTS = "max_statements"
    MAX_DISTINCT_CALLS = "max_distinct_calls"
    MAX_LOCALS = "max_locals"
    MAX_FILE_LINES = "max_file_lines"
    MAX_HELPERS_CONTAINER_MODULES = "max_helpers_container_modules"
    MAX_MAIN_CONTAINER_MODULES = "max_main_container_modules"
    MAX_ROLE_DEPTH = "max_role_depth"
    MAX_POSITIONAL_ARGS = "max_positional_args"
    MAX_ARGUMENTS = "max_arguments"
    MAX_STATEMENTS_GLOBAL = "max_statements_global"
    MAX_SCRIPT_ENTRYPOINT_LINES = "max_script_entrypoint_lines"
    MIN_SHARED_DOMAIN_PREFIX_PACKAGES = "min_shared_domain_prefix_packages"
    MIN_CUSTOM_RULE_TEST_CASES = "min_custom_rule_test_cases"
    MAX_IMPORTED_BINDINGS = "max_imported_bindings"
    MAX_PUBLIC_EXPORTS = "max_public_exports"
    MAX_ROUTE_SCRIPT_LINES = "max_route_script_lines"
    MAX_COMPONENT_SCRIPT_LINES = "max_component_script_lines"
    MAX_STATE_LINES = "max_state_lines"
    MAX_STATE_PUBLIC_MEMBERS = "max_state_public_members"
    MAX_STATE_CELLS = "max_state_cells"
    MAX_TOTAL_RUNES = "max_total_runes"
    MAX_STATE_FUNCTIONS = "max_state_functions"
    MAX_RESOURCE_FAMILIES = "max_resource_families"
    MAX_API_LINES = "max_api_lines"
    MAX_API_EXPORTS = "max_api_exports"


class RuleProjectFacts(Protocol):
    """Discovered-tree facts and requester-bound cross-file queries."""

    @property
    def tree(self) -> ProjectTree:
        """Return immutable facts from the authoritative discovered tree."""
        ...

    def analysis(
        self, *, path: ProjectPath | str | Path, requester: Path | None = None
    ) -> Analysis | None:
        """Return analysis while defaulting to the active invocation requester."""
        ...

    def dataclasses(
        self, *, path: ProjectPath | str | Path, requester: Path | None = None
    ) -> tuple[DataclassFact, ...]:
        """Return dataclass facts while recording the source dependency."""
        ...

    def directory_entries(
        self, *, path: ProjectPath | str | Path, requester: Path | None = None
    ) -> tuple[Path, ...]:
        """Return direct directory entries with requester tracking."""
        ...

    def module_function(
        self,
        *,
        module_name: str,
        function_name: str,
        requester: Path | None = None,
    ) -> ProjectFunctionFact | None:
        """Return a project function contract with requester tracking."""
        ...

    def entrypoint_modules(self, *, requester: Path | None = None) -> tuple[str, ...]:
        """Return configured entrypoint modules with requester tracking."""
        ...

    def python_anchor(
        self, *, path: ProjectPath | str | Path, requester: Path | None = None
    ) -> Path | None:
        """Return the Python ownership anchor with requester tracking."""
        ...

    def exists(self, *, path: ProjectPath | str | Path, requester: Path | None = None) -> bool:
        """Return whether a path exists with requester tracking."""
        ...

    def is_dir(self, *, path: ProjectPath | str | Path, requester: Path | None = None) -> bool:
        """Return whether a path is a directory with requester tracking."""
        ...

    def is_file(self, *, path: ProjectPath | str | Path, requester: Path | None = None) -> bool:
        """Return whether a path is a file with requester tracking."""
        ...

    def glob(
        self,
        *,
        path: ProjectPath | str | Path,
        pattern: str,
        recursive: bool = False,
        requester: Path | None = None,
    ) -> tuple[Path, ...]:
        """Return filesystem glob matches with requester tracking."""
        ...

    def dependencies(self) -> tuple[ProjectDependency, ...]:
        """Return dependencies observed by the shared project analysis."""
        ...

    def dependencies_for(self, *, requester: Path | None = None) -> tuple[ProjectDependency, ...]:
        """Return dependencies for the active or supplied requester."""
        ...


class RuleContext(Protocol):
    """Convenience AST/position toolbox passed to a rule check; may be ignored."""

    @property
    def facts(self) -> FactAnalysis:
        """Return semantic facts for the current file."""
        ...

    @property
    def project(self) -> RuleProjectFacts:
        """Return tree facts and requester-bound cross-file queries."""
        ...

    @property
    def graph(self) -> ArchitectureGraph:
        """Return the evaluation-scoped analyzer-neutral architecture graph."""
        ...

    @property
    def rust(self) -> RustWorkspaceFacts:
        """Return evaluation-scoped Fensu-owned Rust workspace facts."""
        ...

    @property
    def text(self) -> TextAnalysis:
        """Return source-text queries for the current file."""
        ...

    @property
    def syntax(self) -> SyntaxAnalysis:
        """Return backend-neutral syntax queries for the current file."""
        ...

    @property
    def relations(self) -> RelationAnalysis:
        """Return backend-neutral syntax relationships for the current file."""
        ...

    def _memoize[T](self, *, key: str, operation: Callable[[], T]) -> T:
        """Return one value shared by all rules evaluating the current file."""
        ...

    def option[T](self, option: RuleOption[T]) -> T:
        """Return the current value of an option declared by the active rule."""
        ...

    def constraint(self, *, name: str) -> tuple[str, ...]:
        """Return one fixed exhaustive value set declared by the active rule."""
        ...

    def limit(self, *, name: str) -> int:
        """Return one fixed numeric cardinality declared by the active rule."""
        ...

    def custom_rule_registrations(self) -> tuple[CustomRuleRegistration, ...]:
        """Return configured custom-rule declarations owned by the current file."""
        ...

    def fault(
        self,
        *,
        node: ast.AST,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a Fault with line/column/code wired from the node."""
        ...

    def fault_at(
        self,
        *,
        location: SyntaxHandle | SourceLocation | SourceRange,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a Fault from a backend-neutral syntax location."""
        ...

    def fault_for(
        self,
        *,
        path: Path,
        line: int,
        column: int,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a Fault from an explicit backend-neutral source location."""
        ...

    def path_fault(
        self,
        *,
        path: ProjectPath | str | Path | None = None,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a file-level Fault using the active rule metadata."""
        ...

    @property
    def path(self) -> Path:
        """The path of the file currently being checked."""
        ...

    @property
    def repo_root(self) -> Path:
        """The resolved repository root."""
        ...

    @property
    def source(self) -> str:
        """The raw source text of the current file."""
        ...

    def relative_parts(self) -> tuple[str, ...]:
        """The current file's path parts relative to its matched scope root."""
        ...

    def repo_relative_parts(self) -> tuple[str, ...]:
        """The current file's path parts relative to the repository root."""
        ...

    def scope_root(self) -> Path:
        """The configured root that owns the current file."""
        ...

    def scope_roots(self, scope: ScopeName) -> tuple[Path, ...]:
        """The ordered configured roots for one scope category."""
        ...

    def module_parts(self) -> tuple[str, ...]:
        """The current file's complete importable module parts."""
        ...

    def scope(self) -> ScopeName:
        """The configured discovery scope for the current file."""
        ...

    def role_of(self, path: Path | None = None) -> str | None:
        """The current file's role; the path parameter remains for legacy compatibility."""
        ...

    def in_role(self, role: str) -> bool:
        """Whether the current file is within the given role."""
        ...

    def is_entry_module(self) -> bool:
        """Whether the current file is a main/ entry module."""
        ...

    def is_main_module(self) -> bool:
        """Whether the current file is within a main/ package."""
        ...

    def domain(self) -> str | None:
        """The top-level domain of the current file, if any."""
        ...

    def subdomain(self) -> str | None:
        """The subdomain of the current file, if any."""
        ...

    def nodes(self, node_type: type[ast.AST]) -> list[ast.AST]:
        """Nodes of the given type from the shared single-pass index."""
        ...

    def call_name(self, node: ast.Call) -> str | None:
        """The called name of a call node, if resolvable."""
        ...

    def base_name(self, node: ast.expr) -> str | None:
        """The base name of an expression, if resolvable."""
        ...

    def top_level_functions(self, module: ast.Module) -> tuple[ast.AST, ...]:
        """The top-level function definitions of a module."""
        ...

    def non_docstring_body(self, module: ast.Module) -> list[ast.stmt]:
        """A module's body with the leading docstring removed."""
        ...

    def distinct_callees(self, fn: ast.AST) -> frozenset[str]:
        """The distinct callee names invoked within a function."""
        ...

    def assigned_locals(self, fn: ast.AST) -> frozenset[str]:
        """The names assigned as locals within a function."""
        ...

    def complex_comprehensions(self) -> tuple[ast.AST, ...]:
        """Comprehensions that combine generators or nest another comprehension."""
        ...

    def parameter_names(self, fn: ast.AST) -> frozenset[str]:
        """The parameter names of a function."""
        ...

    def inside_loop(self, node: ast.AST) -> bool:
        """Whether a node is lexically inside a loop."""
        ...

    def threshold(self, *, name: Threshold, path: ProjectPath | str | Path | None = None) -> int:
        """The applicable value for a named threshold on the reported path."""
        ...

    def contracts(self) -> Mapping[str, str]:
        """The configured function-name behavior contracts."""
        ...

    def test_scopes(self) -> tuple[str, ...]:
        """The configured test scope vocabulary in declaration order."""
        ...


type RuleCheck = Callable[..., list[Fault]]
