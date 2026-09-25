"""RuleContext implementation for source-independent project rule execution."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn, cast

from fensu.analysis.models import SourceLocation, SourceRange, SyntaxHandle
from fensu.config.constants import DEFAULT_TARGET_ROOT
from fensu.config.main.resolve_threshold import resolve_threshold
from fensu.config.models import Config, ThresholdResolution
from fensu.discovery.models import DiscoveredTree, RepoRoot
from fensu.evaluation.classes.rule_project import RuleProjectView
from fensu.evaluation.constants import PARENT_PATH_PART, PROJECT_REQUESTER_NAME
from fensu.evaluation.exceptions import ProjectContextUnavailableError
from fensu.evaluation.models import ThresholdOverrideUse
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    Fault,
    FilePosition,
    ProjectPath,
    RuleConstraint,
    RuleLimit,
    RuleOption,
    RuleSpec,
)
from fensu.rules.authoring.types import RuleOptionValue, Threshold


class ProjectRuleContext:
    """Expose project facts while failing clearly for file-only context state."""

    def __init__(
        self,
        *,
        tree: DiscoveredTree,
        analysis: EvaluationProjectAnalysis,
        config: Config,
        rule: RuleSpec,
    ) -> None:
        self._config = config
        self._rule = rule
        self._project_root: RepoRoot = (
            tree.repo_root if tree.project_root is None else tree.project_root
        )
        self._requester = tree.repo_root.path / PROJECT_REQUESTER_NAME
        self._project = RuleProjectView(
            tree=tree,
            analysis=analysis,
            requester=self._requester,
            config=config,
        )
        self.threshold_override_uses: list[ThresholdOverrideUse] = []
        self._analysis = analysis

    @property
    def project(self) -> RuleProjectView:
        """Return tree facts and queries bound to the project-rule requester."""

        return self._project

    @property
    def graph(self) -> ArchitectureGraph:
        """Return lazy analyzer-neutral import graph facts without a source anchor."""

        return self._analysis.architecture_graph(requester=self._requester)

    @property
    def facts(self) -> Any:
        """Fail because a project invocation has no current file facts."""

        return self._file_only("facts")

    @property
    def text(self) -> Any:
        """Fail because a project invocation has no current source text analysis."""

        return self._file_only("text")

    @property
    def syntax(self) -> Any:
        """Fail because a project invocation has no current syntax analysis."""

        return self._file_only("syntax")

    @property
    def relations(self) -> Any:
        """Fail because a project invocation has no current syntax relationships."""

        return self._file_only("relations")

    @property
    def path(self) -> Path:
        """Fail because a project invocation has no current file path."""

        return self._file_only("path")

    @property
    def source(self) -> str:
        """Fail because a project invocation has no current source."""

        return self._file_only("source")

    def option[T](self, option: RuleOption[T]) -> T:
        """Return an option declared by the active project rule."""

        if not any(declared is option for declared in self._rule.options):
            raise RuleDefinitionError(
                f"rule {self._rule.code} requested undeclared option {option.name}"
            )
        value: RuleOptionValue = self._config.rule_options[self._rule.code][option.name]
        return cast(T, value)

    def constraint(self, *, name: str) -> tuple[str, ...]:
        """Return one fixed constraint declared by the active rule."""

        constraint: RuleConstraint | None = next(
            (item for item in self._rule.constraints if item.name == name), None
        )
        if constraint is None:
            raise RuleDefinitionError(
                f"rule {self._rule.code} requested undeclared constraint {name}"
            )
        return constraint.values

    def limit(self, *, name: str) -> int:
        """Return one fixed limit declared by the active rule."""

        limit: RuleLimit | None = next(
            (item for item in self._rule.limits if item.name == name), None
        )
        if limit is None:
            raise RuleDefinitionError(f"rule {self._rule.code} requested undeclared limit {name}")
        return limit.value

    def path_fault(
        self,
        *,
        path: ProjectPath | str | None = None,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a project-rule fault against one confined project path."""

        if path is None:
            raise ProjectContextUnavailableError(
                "project rule path_fault requires a ProjectPath or project-relative string"
            )
        return Fault(
            code=self._rule.code,
            path=self._project.absolute_path(path),
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
        """Construct a project finding from an analyzer-neutral source location."""

        if isinstance(location, SyntaxHandle):
            raise ProjectContextUnavailableError(
                "RuleContext.fault_at cannot resolve a SyntaxHandle during project rule "
                "evaluation; use its SourceRange or SourceLocation"
            )
        if isinstance(location, SourceRange):
            return self.fault_for(
                path=location.path,
                line=location.start.line,
                column=location.start.column,
                message=message,
                remediation=remediation,
            )
        return self.fault_for(
            path=(
                location.path
                if location.path.is_absolute()
                else self._project.absolute_path(ProjectPath(location.path.as_posix()))
            ),
            line=location.line,
            column=location.column,
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
        """Construct a project finding for an explicit confined source position."""

        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or PARENT_PATH_PART in path.parts
            or not path.is_relative_to(self._project_root.path)
        ):
            raise ProjectContextUnavailableError(
                "project rule fault_for requires an absolute path confined to the analyzed project"
            )
        return Fault(
            code=self._rule.code,
            path=path,
            message=self._rule.message if message is None else message,
            line=line,
            column=column,
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    def threshold(self, *, name: Threshold, path: ProjectPath | str | Path | None = None) -> int:
        """Resolve a threshold for an explicit confined project path."""

        if path is None:
            raise ProjectContextUnavailableError(
                "project rule threshold requires an explicit confined project path"
            )
        if isinstance(path, Path):
            raise ProjectContextUnavailableError(
                "project rule threshold path must be a ProjectPath or project-relative string"
            )
        project_path: ProjectPath = path if isinstance(path, ProjectPath) else ProjectPath(path)
        position: FilePosition | None = self._project.tree.position(project_path)
        resolution: ThresholdResolution = resolve_threshold(
            config=self._config,
            name=name,
            path=project_path.value,
            role=None if position is None else position.role,
        )
        if (
            resolution.matched_pattern is not None
            and resolution.reason is not None
            and resolution.override_order is not None
        ):
            visible_path: str = (
                resolution.repository_path
                if self._config.target_root == DEFAULT_TARGET_ROOT
                else f"{self._config.target_root}/{resolution.repository_path}"
            )
            self.threshold_override_uses.append(
                ThresholdOverrideUse(
                    threshold=resolution.threshold,
                    effective_value=resolution.effective_value,
                    matched_pattern=resolution.matched_pattern,
                    reason=resolution.reason,
                    override_order=resolution.override_order,
                    repository_path=visible_path,
                )
            )
        return resolution.effective_value

    def contracts(self) -> Mapping[str, str]:
        """Return configured function behavior contracts."""

        return self._config.contracts

    def test_scopes(self) -> tuple[str, ...]:
        """Return configured test scope vocabulary."""

        return self._config.test_scopes

    def _file_only(self, name: str) -> NoReturn:
        raise ProjectContextUnavailableError(
            f"RuleContext.{name} is unavailable during project rule evaluation because there is "
            "no current file"
        )
