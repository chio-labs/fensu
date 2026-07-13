"""Authoring type-layer declarations: taxonomy, thresholds, and the check contract."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from strata.discovery.types import ScopeName

if TYPE_CHECKING:
    from strata.analysis.models import SourceLocation, SourceRange, SyntaxHandle
    from strata.analysis.types import (
        FactAnalysis,
        ProjectAnalysis,
        RelationAnalysis,
        SyntaxAnalysis,
        TextAnalysis,
    )
    from strata.rules.authoring.models import Fault


class Family(StrEnum):
    """The rule family a rule belongs to."""

    LAYERS = "layers"
    ROLES = "roles"
    SHAPE = "shape"
    NAMING = "naming"
    HYGIENE = "hygiene"
    TESTS = "tests"
    ANNOTATIONS = "annotations"
    CUSTOM = "custom"


class Severity(StrEnum):
    """The severity assigned to a fault."""

    ERROR = "error"
    WARNING = "warning"


class RuleKind(StrEnum):
    """Whether a rule ships with strata or is authored downstream."""

    CORE = "core"
    CUSTOM = "custom"


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


class RuleContext(Protocol):
    """Convenience AST/position toolbox passed to a rule check; may be ignored."""

    @property
    def facts(self) -> FactAnalysis:
        """Return semantic facts for the current file."""
        ...

    @property
    def project(self) -> ProjectAnalysis:
        """Return dependency-recording cross-file and filesystem queries."""
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
        path: Path | None = None,
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
        """The role name of the given path (or the current file)."""
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

    def threshold(self, *, name: Threshold, path: Path | None = None) -> int:
        """The applicable value for a named threshold on the reported path."""
        ...

    def contracts(self) -> Mapping[str, str]:
        """The configured function-name behavior contracts."""
        ...


class RuleCheck(Protocol):
    """A rule implementation invoked with explicit module and context names."""

    def __call__(self, *, module: ast.Module, ctx: RuleContext) -> list[Fault]:
        """Return faults found in one parsed module."""
        ...
