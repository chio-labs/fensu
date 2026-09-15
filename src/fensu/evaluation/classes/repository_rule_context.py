"""RuleContext implementation for one cross-target repository rule."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn, cast

from fensu.analysis.models import SourceLocation, SourceRange
from fensu.config.models import Config
from fensu.evaluation.classes.repository_rule_targets import RepositoryRuleTargets
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import (
    CustomRuleRegistration,
    Fault,
    ProjectPath,
    RuleConstraint,
    RuleLimit,
    RuleOption,
    RuleSpec,
)
from fensu.rules.authoring.types import RuleOptionValue


class RepositoryRuleContext:
    """Expose only explicit target handles and repository-confined diagnostics."""

    def __init__(
        self, *, root: Path, config: Config, rule: RuleSpec, targets: RepositoryRuleTargets
    ) -> None:
        self._root = root.resolve()
        self._config = config
        self._rule = rule
        self._targets = targets

    @property
    def targets(self) -> RepositoryRuleTargets:
        """Return explicit target handles for this repository invocation."""

        return self._targets

    @property
    def facts(self) -> NoReturn:
        return self._unavailable("facts")

    @property
    def project(self) -> NoReturn:
        return self._unavailable("project")

    @property
    def graph(self) -> NoReturn:
        return self._unavailable("graph")

    @property
    def python(self) -> NoReturn:
        return self._unavailable("python")

    @property
    def rust(self) -> NoReturn:
        return self._unavailable("rust")

    @property
    def web(self) -> NoReturn:
        return self._unavailable("web")

    @property
    def text(self) -> NoReturn:
        return self._unavailable("text")

    @property
    def syntax(self) -> NoReturn:
        return self._unavailable("syntax")

    @property
    def relations(self) -> NoReturn:
        return self._unavailable("relations")

    @property
    def repo_root(self) -> Path:
        """Return the configured repository root."""

        return self._root

    def option[T](self, option: RuleOption[T]) -> T:
        """Return one declared typed repository-rule option."""

        if not any(declared is option for declared in self._rule.options):
            raise RuleDefinitionError(
                f"rule {self._rule.code} requested undeclared option {option.name}"
            )
        value: RuleOptionValue = self._config.rule_options[self._rule.code][option.name]
        return cast(T, value)

    def constraint(self, *, name: str) -> tuple[str, ...]:
        """Return one fixed exhaustive repository-rule value set."""

        value: RuleConstraint | None = next(
            (item for item in self._rule.constraints if item.name == name), None
        )
        if value is None:
            raise RuleDefinitionError(
                f"rule {self._rule.code} requested undeclared constraint {name}"
            )
        return value.values

    def limit(self, *, name: str) -> int:
        """Return one fixed repository-rule cardinality."""

        value: RuleLimit | None = next(
            (item for item in self._rule.limits if item.name == name), None
        )
        if value is None:
            raise RuleDefinitionError(f"rule {self._rule.code} requested undeclared limit {name}")
        return value.value

    def custom_rule_registrations(self) -> tuple[CustomRuleRegistration, ...]:
        """Repository rules do not expose file-owned registration coverage."""

        return ()

    def path_fault(
        self,
        *,
        path: ProjectPath | str | None = None,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct one repository-relative path diagnostic."""

        relative: ProjectPath | None = (
            None if path is None else path if isinstance(path, ProjectPath) else ProjectPath(path)
        )
        return Fault(
            code=self._rule.code,
            path=self._root if relative is None else self._root.joinpath(*relative.parts),
            message=self._rule.message if message is None else message,
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    def fault_at(
        self,
        *,
        location: SourceLocation | SourceRange,
        message: str | None = None,
        remediation: str | None = None,
    ) -> Fault:
        """Construct a diagnostic from a repository-relative stable location."""

        if isinstance(location, SourceRange):
            path: Path = location.path
            line: int = location.start.line
            column: int = location.start.column
        elif isinstance(location, SourceLocation):
            path = location.path
            line = location.line
            column = location.column
        else:
            raise RuleDefinitionError(
                "repository rule fault_at requires a SourceLocation or SourceRange"
            )
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
        """Construct one repository-confined exact-location diagnostic."""

        absolute: Path = (
            path if path.is_absolute() else self._root / ProjectPath(path.as_posix()).value
        )
        resolved: Path = absolute.resolve()
        if not resolved.is_relative_to(self._root):
            raise RuleDefinitionError("repository rule fault path escapes the repository")
        return Fault(
            code=self._rule.code,
            path=resolved,
            message=self._rule.message if message is None else message,
            line=line,
            column=column,
            remediation=self._rule.remediation if remediation is None else remediation,
        )

    def fault(self, *, node: object, **_kwargs: object) -> NoReturn:
        """Reject parser-node diagnostics for repository rules."""

        del node
        return self._unavailable("fault")

    def _memoize[T](self, *, key: str, operation: object) -> T:
        del key, operation
        return self._unavailable("_memoize")

    def _unavailable(self, name: str) -> NoReturn:
        raise RuleDefinitionError(f"RuleContext.{name} is unavailable for repository rules")
