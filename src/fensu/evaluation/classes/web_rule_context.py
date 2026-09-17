"""RuleContext implementation backed only by serialized Fensu-owned Web facts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn, cast

from fensu.analysis.models import SourceLocation, SourceRange, SyntaxHandle
from fensu.config.models import Config
from fensu.evaluation.classes.web_dependency_observer import WebDependencyObserver
from fensu.evaluation.classes.web_rule_project import WebRuleProjectView
from fensu.evaluation.constants import PROJECT_REQUESTER_NAME
from fensu.evaluation.exceptions import ProjectContextUnavailableError
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    CustomRuleRegistration,
    Fault,
    FilePosition,
    ProjectPath,
    ProjectTree,
    RuleConstraint,
    RuleLimit,
    RuleOption,
    RuleSpec,
    WebFileFacts,
    WebWorkspaceFacts,
)
from fensu.rules.authoring.types import RuleOptionValue, Threshold


class WebRuleContext:
    """Execute one typed custom rule without exposing parser implementation objects."""

    def __init__(
        self,
        *,
        root: Path,
        tree: ProjectTree,
        graph: ArchitectureGraph,
        workspace: WebWorkspaceFacts,
        config: Config,
        rule: RuleSpec,
        file_facts: WebFileFacts | None,
        observations: list[dict[str, str]],
    ) -> None:
        self._root = root.resolve()
        self._rule = rule
        self._config = config
        self._file_facts = file_facts
        self._requester = (
            PROJECT_REQUESTER_NAME if file_facts is None else file_facts.file.path.value
        )
        self._project = WebRuleProjectView(
            root=self._root,
            tree=tree,
            requester=self._requester,
            observations=observations,
        )
        observer: WebDependencyObserver = WebDependencyObserver(
            requester=self._requester, observations=observations
        )
        self._web = workspace.observed(observer)
        self._graph = graph.observed(observer)

    @property
    def project(self) -> WebRuleProjectView:
        """Return the common project tree bound to the active requester."""

        return self._project

    @property
    def web(self) -> WebWorkspaceFacts:
        """Return Fensu-owned TypeScript, JavaScript, and Svelte facts."""

        return self._web

    @property
    def rust(self) -> NoReturn:
        """Fail because Cargo facts are unavailable for web targets."""

        return self._unavailable("rust")

    @property
    def facts(self) -> WebFileFacts:
        """Return owned facts for the current file invocation."""

        facts: WebFileFacts = self._require_file("facts")
        observed: WebFileFacts | None = self._web.file(facts.file)
        if observed is None:
            raise ProjectContextUnavailableError(
                "Current Web file is absent from the authoritative fact payload"
            )
        return observed

    @property
    def path(self) -> Path:
        """Return the absolute current Web file path."""

        return self._root / self._require_file("path").file.path.value

    @property
    def source(self) -> str:
        """Return source transferred with the current Web file facts."""

        return self.facts.source

    @property
    def repo_root(self) -> Path:
        """Return the analyzed web target root."""

        return self._root

    @property
    def graph(self) -> ArchitectureGraph:
        """Return native-resolved imports through the common architecture graph."""

        return self._graph

    @property
    def text(self) -> NoReturn:
        """Fail clearly until the generic text facade accepts serialized sources."""

        return self._unavailable("text")

    @property
    def syntax(self) -> NoReturn:
        """Fail because parser-specific Web syntax is not a public contract."""

        return self._unavailable("syntax")

    @property
    def relations(self) -> NoReturn:
        """Fail because parser-specific Web syntax is not a public contract."""

        return self._unavailable("relations")

    def option[T](self, option: RuleOption[T]) -> T:
        """Return a validated option declared by the active custom rule."""

        if not any(declared is option for declared in self._rule.options):
            raise RuleDefinitionError(
                f"rule {self._rule.code} requested undeclared option {option.name}"
            )
        value: RuleOptionValue = self._config.rule_options[self._rule.code][option.name]
        return cast(T, value)

    def constraint(self, *, name: str) -> tuple[str, ...]:
        """Return one fixed constraint declared by the active rule."""

        value: RuleConstraint | None = next(
            (item for item in self._rule.constraints if item.name == name), None
        )
        if value is None:
            raise RuleDefinitionError(
                f"rule {self._rule.code} requested undeclared constraint {name}"
            )
        return value.values

    def limit(self, *, name: str) -> int:
        """Return one fixed limit declared by the active rule."""

        value: RuleLimit | None = next(
            (item for item in self._rule.limits if item.name == name), None
        )
        if value is None:
            raise RuleDefinitionError(f"rule {self._rule.code} requested undeclared limit {name}")
        return value.value

    def path_fault(
        self,
        *,
        path: ProjectPath | str | Path | None = None,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a confined file-level finding with active rule metadata."""

        resolved: Path
        if path is None:
            resolved = self.path
        elif isinstance(path, Path):
            resolved = path if path.is_absolute() else self._project.absolute_path(path.as_posix())
        else:
            resolved = self._project.absolute_path(path)
        self._confined(resolved)
        return Fault(
            code=self._rule.code,
            path=resolved,
            message=self._rule.message if message is None else message,
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    def fault_at(
        self,
        *,
        location: SyntaxHandle | SourceLocation | SourceRange,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a finding from an owned Web location."""

        if isinstance(location, SyntaxHandle):
            raise ProjectContextUnavailableError(
                "Web custom rules cannot resolve parser-specific SyntaxHandle values"
            )
        path: Path
        line: int
        column: int
        if isinstance(location, SourceRange):
            path = location.path
            line = location.start.line
            column = location.start.column
        else:
            path = location.path
            line = location.line
            column = location.column
        absolute: Path = (
            path if path.is_absolute() else self._project.absolute_path(path.as_posix())
        )
        return self.fault_for(
            path=absolute,
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
        """Construct a finding at one explicit confined source position."""

        self._confined(path)
        return Fault(
            code=self._rule.code,
            path=path,
            line=line,
            column=column,
            message=self._rule.message if message is None else message,
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    def relative_parts(self) -> tuple[str, ...]:
        """Return the current file path relative to its configured scope root."""

        facts: WebFileFacts = self._require_file("relative_parts")
        position: FilePosition | None = self._project.tree.position(facts.file.path)
        if position is None:
            return facts.file.path.parts
        return facts.file.path.parts[len(position.scope_root.parts) :]

    def ownership_root(self) -> Path | None:
        """Return the effective ownership root for the current file."""

        position: FilePosition | None = self._current_position()
        return (
            None
            if position is None or position.ownership_root is None
            else self._root / position.ownership_root.value
        )

    def ownership_roots(self) -> tuple[Path, ...]:
        """Return configured ownership roots."""

        return tuple(self._root / root for root in self._config.ownership_roots)

    def ownership_relative_parts(self) -> tuple[str, ...]:
        """Return path parts below the effective ownership root."""

        position: FilePosition | None = self._current_position()
        if position is None:
            return self.relative_parts()
        return position.ownership_relative_parts

    def ownership_root_declaration(self) -> str | None:
        """Return the matched ownership-root declaration."""

        position: FilePosition | None = self._current_position()
        return None if position is None else position.ownership_root_declaration

    def _current_position(self) -> FilePosition | None:
        facts: WebFileFacts = self._require_file("ownership position")
        return self._project.tree.position(facts.file.path)

    def repo_relative_parts(self) -> tuple[str, ...]:
        """Return project-relative parts for the current Web file."""

        return self._require_file("repo_relative_parts").file.path.parts

    def module_parts(self) -> tuple[str, ...]:
        """Return the Fensu-owned Web module identity."""

        return tuple(self.facts.module.split("."))

    def custom_rule_registrations(self) -> tuple[CustomRuleRegistration, ...]:
        """Return no declaration ownership facts for Web source files."""

        return ()

    def contracts(self) -> Mapping[str, str]:
        """Return configured naming contracts."""

        return self._config.contracts

    def test_scopes(self) -> tuple[str, ...]:
        """Return configured test scope names."""

        return self._config.test_scopes

    def threshold(self, *, name: Threshold, path: ProjectPath | str | Path | None = None) -> int:
        """Fail until Web custom thresholds have an explicit ownership contract."""

        del name, path
        return self._unavailable("threshold")

    def _require_file(self, name: str) -> WebFileFacts:
        if self._file_facts is None:
            raise ProjectContextUnavailableError(
                f"RuleContext.{name} is unavailable during project rule evaluation because "
                "there is no current file"
            )
        return self._file_facts

    def _confined(self, path: Path) -> None:
        if not path.is_absolute() or not path.resolve().is_relative_to(self._root):
            raise ProjectContextUnavailableError(
                "Web custom-rule faults must be confined to the analyzed project"
            )

    def _unavailable(self, name: str) -> NoReturn:
        raise ProjectContextUnavailableError(
            f"RuleContext.{name} is unavailable for serialized Web custom rules"
        )
