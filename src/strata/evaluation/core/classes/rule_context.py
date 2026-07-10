"""Concrete RuleContext implementation used while evaluating one rule/file pair."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.models import SourceLocation, SourceRange, SyntaxHandle
from strata.analysis.core.types import Analysis
from strata.config.core.models import Config
from strata.discovery.core.models import RepoRoot
from strata.discovery.core.types import ScopeName
from strata.evaluation.core.helpers import ast_access
from strata.evaluation.core.models import ParsedModule
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Threshold


class EvaluationRuleContext:
    """RuleContext backed by one parsed module, config, repo root, and active rule."""

    def __init__(
        self,
        *,
        parsed_module: ParsedModule,
        config: Config,
        repo_root: RepoRoot,
        rule: RuleSpec,
    ) -> None:
        """Bind context facts for one rule invocation."""

        self._parsed_module: ParsedModule = parsed_module
        self._config: Config = config
        self._repo_root: RepoRoot = repo_root
        self._rule: RuleSpec = rule

    @property
    def _analysis(self) -> Analysis:
        """Return the private replaceable analysis facade for the current file."""

        return self._parsed_module.analysis

    def fault(
        self,
        node: ast.AST,
        *,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a Fault with active-rule code and AST location."""

        return Fault(
            code=self._rule.code,
            path=self.path,
            message=self._rule.message if message is None else message,
            line=getattr(node, "lineno", None),
            column=getattr(node, "col_offset", None),
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    def fault_at(
        self,
        location: SyntaxHandle | SourceLocation | SourceRange,
        *,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a Fault from a backend-neutral syntax location."""

        if isinstance(location, SyntaxHandle):
            source_range: SourceRange = self._analysis.syntax.range(location)
            path: Path = source_range.path
            line: int = source_range.start.line
            column: int = source_range.start.column
        elif isinstance(location, SourceRange):
            path = location.path
            line = location.start.line
            column = location.start.column
        else:
            path = location.path
            line = location.line
            column = location.column
        return self.fault_for(
            path=path,
            line=line,
            column=column,
            message=message,
            remediation=remediation,
        )

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

        return Fault(
            code=self._rule.code,
            path=path,
            message=self._rule.message if message is None else message,
            line=line,
            column=column,
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    def path_fault(self, *, message: str | None = None, remediation: str | None = None) -> Fault:
        """Construct a file-level Fault using the active rule metadata."""

        return Fault(
            code=self._rule.code,
            path=self.path,
            message=self._rule.message if message is None else message,
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    @property
    def path(self) -> Path:
        """The path of the file currently being checked."""

        return self._parsed_module.scoped_file.path

    @property
    def repo_root(self) -> Path:
        """The resolved repository root."""

        return self._repo_root.path

    @property
    def source(self) -> str:
        """The raw source text of the current file."""

        return self._parsed_module.source

    def relative_parts(self) -> tuple[str, ...]:
        """The current file's path parts relative to its matched scope root."""

        return self._parsed_module.scoped_file.relative_parts

    def scope(self) -> ScopeName:
        """The configured discovery scope for the current file."""

        return self._parsed_module.scoped_file.scope

    def role_of(self, path: Path | None = None) -> str | None:
        """The role name of the current file; explicit path support arrives with ctx routing."""

        if path is not None and path != self.path:
            return None
        return self._parsed_module.position.role

    def in_role(self, role: str) -> bool:
        """Whether the current file is within the given role."""

        return self.role_of() == role

    def is_entry_module(self) -> bool:
        """Whether the current file is a main/ entry module."""

        return self._parsed_module.position.is_entry_module

    def is_main_module(self) -> bool:
        """Whether the current file is within a main/ package."""

        return self._parsed_module.position.is_main_module

    def domain(self) -> str | None:
        """The top-level domain of the current file, if any."""

        return self._parsed_module.position.domain

    def subdomain(self) -> str | None:
        """The subdomain of the current file, if any."""

        return self._parsed_module.position.subdomain

    def nodes(self, node_type: type[ast.AST]) -> list[ast.AST]:
        """Nodes of the given type from the shared single-pass index."""

        return list(self._parsed_module.node_index.get(node_type, ()))

    def call_name(self, node: ast.Call) -> str | None:
        """The called name of a call node, if resolvable."""

        return ast_access.call_name(node)

    def base_name(self, node: ast.expr) -> str | None:
        """The base name of an expression, if resolvable."""

        return ast_access.base_name(node)

    def top_level_functions(self, module: ast.Module) -> tuple[ast.AST, ...]:
        """The top-level function definitions of a module."""

        return ast_access.top_level_functions(module)

    def non_docstring_body(self, module: ast.Module) -> list[ast.stmt]:
        """A module's body with the leading docstring removed."""

        return ast_access.non_docstring_body(module)

    def distinct_callees(self, fn: ast.AST) -> frozenset[str]:
        """The distinct callee names invoked within a function."""

        return ast_access.distinct_callees(fn)

    def assigned_locals(self, fn: ast.AST) -> frozenset[str]:
        """The names assigned as locals within a function."""

        return ast_access.assigned_locals(fn)

    def complex_comprehensions(self) -> tuple[ast.AST, ...]:
        """Comprehensions that combine generators or nest another comprehension."""

        return ast_access.complex_comprehensions(self._parsed_module.node_index)

    def parameter_names(self, fn: ast.AST) -> frozenset[str]:
        """The parameter names of a function."""

        return ast_access.parameter_names(fn)

    def inside_loop(self, node: ast.AST) -> bool:
        """Whether a node is lexically inside a loop."""

        return ast_access.inside_loop(node=node, parent_by_node=self._parsed_module.parent_by_node)

    def threshold(self, name: Threshold) -> int:
        """The applicable global or per-role threshold for the current file."""

        role: str | None = self.role_of()
        if role is not None:
            role_thresholds: Mapping[Threshold, int] | None = self._config.role_thresholds.get(role)
            if role_thresholds is not None and name in role_thresholds:
                return role_thresholds[name]
        return self._config.thresholds[name]

    def contracts(self) -> Mapping[str, str]:
        """Return configured function-name behavior contracts."""

        return self._config.contracts
