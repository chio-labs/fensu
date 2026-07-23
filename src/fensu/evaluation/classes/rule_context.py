"""Concrete RuleContext implementation used while evaluating one rule/file pair."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from fensu.analysis.models import SourceLocation, SourceRange, SyntaxHandle
from fensu.analysis.types import (
    FactAnalysis,
    ProjectAnalysis,
    RelationAnalysis,
    SyntaxAnalysis,
    TextAnalysis,
)
from fensu.config.main.resolve_threshold import resolve_threshold
from fensu.config.models import Config, ThresholdResolution
from fensu.discovery.constants import (
    INIT_MODULE_FILE_NAME,
    ROLE_FILE_TO_NAME,
    SNAPSHOT_TABLE,
)
from fensu.discovery.models import ProjectLayout, RepoRoot
from fensu.discovery.types import RoleName, ScopeName
from fensu.evaluation._helpers import ast_access
from fensu.evaluation.models import ParsedModule, ThresholdOverrideUse
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import Fault, RuleOption, RuleSpec
from fensu.rules.authoring.types import RuleOptionValue, Threshold

_POSIX_PATH_SEPARATOR: str = "/"
_ROLE_DIRECTORY_NAMES: frozenset[str] = frozenset(role.value for role in RoleName)


class EvaluationRuleContext:
    """RuleContext backed by one parsed module, config, repo root, and active rule."""

    def __init__(
        self,
        *,
        parsed_module: ParsedModule,
        config: Config,
        repo_root: RepoRoot,
        layout: ProjectLayout,
        rule: RuleSpec,
        project: ProjectAnalysis,
        file_cache: dict[str, object],
        threshold_override_uses: list[ThresholdOverrideUse],
    ) -> None:
        """Bind context facts for one rule invocation."""

        self._parsed_module: ParsedModule = parsed_module
        self._config: Config = config
        self._repo_root: RepoRoot = repo_root
        self._layout: ProjectLayout = layout
        self._rule: RuleSpec = rule
        self.__project: ProjectAnalysis = project
        self._file_cache: dict[str, Any] = file_cache
        self._threshold_override_uses: list[ThresholdOverrideUse] = threshold_override_uses

    @property
    def facts(self) -> FactAnalysis:
        """Return semantic facts for the current file."""

        return self._parsed_module.analysis.facts

    @property
    def project(self) -> ProjectAnalysis:
        """Return dependency-recording cross-file and filesystem queries."""

        return self.__project

    @property
    def text(self) -> TextAnalysis:
        """Return source-text queries for the current file."""

        return self._parsed_module.analysis.text

    @property
    def syntax(self) -> SyntaxAnalysis:
        """Return backend-neutral syntax queries for the current file."""

        return self._parsed_module.analysis.syntax

    @property
    def relations(self) -> RelationAnalysis:
        """Return backend-neutral syntax relationships for the current file."""

        return self._parsed_module.analysis.relations

    def _memoize[T](self, *, key: str, operation: Callable[[], T]) -> T:
        """Return one value shared by all rules evaluating the current file."""

        if key not in self._file_cache:
            self._file_cache[key] = operation()
        return self._file_cache[key]

    def option[T](self, option: RuleOption[T]) -> T:
        """Return the current value of an option declared by the active rule."""

        if not any(declared is option for declared in self._rule.options):
            raise RuleDefinitionError(
                f"rule {self._rule.code} requested undeclared option {option.name}"
            )
        value: RuleOptionValue = self._config.rule_options[self._rule.code][option.name]
        return cast(T, value)

    def fault(
        self,
        *,
        node: ast.AST,
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
        *,
        location: SyntaxHandle | SourceLocation | SourceRange,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a Fault from a backend-neutral syntax location."""

        if isinstance(location, SyntaxHandle):
            source_range: SourceRange = self.syntax.range(location)
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

    def path_fault(
        self,
        *,
        path: Path | None = None,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a file-level Fault using the active rule metadata."""

        return Fault(
            code=self._rule.code,
            path=self.path if path is None else path,
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

    def repo_relative_parts(self) -> tuple[str, ...]:
        """The current file's path parts relative to the repository root."""

        return self._memoize(
            key="repo_relative_parts", operation=self._computed_repo_relative_parts
        )

    def _computed_repo_relative_parts(self) -> tuple[str, ...]:
        value: str | None = SNAPSHOT_TABLE.relative_path(path=self.path, repo_root=self.repo_root)
        if value is not None:
            return tuple(value.split(_POSIX_PATH_SEPARATOR))
        return self.path.relative_to(self.repo_root).parts

    def scope_root(self) -> Path:
        """The configured root that owns the current file."""

        return self._parsed_module.scoped_file.root

    def scope_roots(self, scope: ScopeName) -> tuple[Path, ...]:
        """The ordered configured roots for one scope category."""

        if scope is ScopeName.ROOT:
            return tuple(source.path for source in self._layout.runtime_sources)
        if scope is ScopeName.TEST:
            return tuple(root.path for root in self._layout.test_roots)
        return tuple(source.path for source in self._layout.tooling_sources)

    def module_parts(self) -> tuple[str, ...]:
        """The current file's complete importable module parts."""

        return self._memoize(key="module_parts", operation=self._computed_module_parts)

    def _computed_module_parts(self) -> tuple[str, ...]:
        root_parts: tuple[str, ...] = self.scope_root().parts
        path_parts: tuple[str, ...] = self.path.parts
        if len(root_parts) > 1 and path_parts[: len(root_parts)] == root_parts:
            relative_parts: tuple[str, ...] = path_parts[len(root_parts) - 1 :]
        else:
            relative_parts = self.path.relative_to(self.scope_root().parent).parts
        parts: tuple[str, ...] = (*relative_parts[:-1], self.path.stem)
        return (
            parts[:-1]
            if parts and parts[-1] == INIT_MODULE_FILE_NAME.removesuffix(".py")
            else parts
        )

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

        return list(self._parsed_module.syntax_artifacts.node_index.get(node_type, ()))

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

        return ast_access.complex_comprehensions(self._parsed_module.syntax_artifacts.node_index)

    def parameter_names(self, fn: ast.AST) -> frozenset[str]:
        """The parameter names of a function."""

        return ast_access.parameter_names(fn)

    def inside_loop(self, node: ast.AST) -> bool:
        """Whether a node is lexically inside a loop."""

        return ast_access.inside_loop(
            node=node,
            parent_by_node=self._parsed_module.syntax_artifacts.parent_by_node,
        )

    def threshold(self, *, name: Threshold, path: Path | None = None) -> int:
        """The applicable path, role, or global threshold for a reported path."""

        resolution: ThresholdResolution = self._resolved_threshold(name=name, path=path)
        if (
            resolution.matched_pattern is not None
            and resolution.reason is not None
            and resolution.override_order is not None
        ):
            self._threshold_override_uses.append(
                ThresholdOverrideUse(
                    threshold=resolution.threshold,
                    effective_value=resolution.effective_value,
                    matched_pattern=resolution.matched_pattern,
                    reason=resolution.reason,
                    override_order=resolution.override_order,
                    repository_path=resolution.repository_path,
                )
            )
        return resolution.effective_value

    def _resolved_threshold(self, *, name: Threshold, path: Path | None) -> ThresholdResolution:
        relative_path, role = self._threshold_position(path=path)
        return resolve_threshold(config=self._config, name=name, path=relative_path, role=role)

    def _threshold_position(self, *, path: Path | None) -> tuple[str, str | None]:
        if path is None:
            return self._memoize(key="threshold:own_position", operation=self._own_position)
        return (
            path.relative_to(self.repo_root).as_posix(),
            _role_for_path(path=path, scope_root=self.scope_root()),
        )

    def _own_position(self) -> tuple[str, str | None]:
        value: str | None = SNAPSHOT_TABLE.relative_path(path=self.path, repo_root=self.repo_root)
        if value is None:
            value = self.path.relative_to(self.repo_root).as_posix()
        return (value, self.role_of())

    def contracts(self) -> Mapping[str, str]:
        """Return configured function-name behavior contracts."""

        return self._config.contracts


def _role_for_path(*, path: Path, scope_root: Path) -> str | None:
    parts: tuple[str, ...] = path.relative_to(scope_root).parts
    for part in parts[:-1]:
        if part in _ROLE_DIRECTORY_NAMES:
            return part
    return ROLE_FILE_TO_NAME.get(parts[-1])
