"""Remove temporary repository paths from public harness results."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from fensu.analysis.models import ProjectDependency
from fensu.rules.authoring.models import Fault
from fensu.rules.testing.constants import CURRENT_PATH_PART, PARENT_PATH_PART
from fensu.rules.testing.exceptions import RuleHarnessError
from fensu.rules.testing.models import RuleResult


def remap_rule_result(
    *,
    faults: tuple[Fault, ...],
    dependencies: tuple[ProjectDependency, ...],
    repo_root: Path,
) -> RuleResult:
    """Return one result containing only stable repository-relative paths."""

    return RuleResult(
        faults=tuple(_remap_fault(fault=fault, repo_root=repo_root) for fault in faults),
        dependencies=tuple(
            _remap_dependency(dependency=dependency, repo_root=repo_root)
            for dependency in dependencies
        ),
    )


def _remap_fault(*, fault: Fault, repo_root: Path) -> Fault:
    return Fault(
        code=fault.code,
        path=_relative_path(path=fault.path, repo_root=repo_root),
        message=fault.message,
        line=fault.line,
        column=fault.column,
        remediation=fault.remediation,
    )


def _remap_dependency(*, dependency: ProjectDependency, repo_root: Path) -> ProjectDependency:
    answer: None | bool | str | tuple[Path, ...] = dependency.answer
    if isinstance(answer, tuple):
        answer = tuple(_relative_path(path=path, repo_root=repo_root) for path in answer)
    return ProjectDependency(
        requester=_relative_path(path=dependency.requester, repo_root=repo_root),
        query_path=_relative_path(path=dependency.query_path, repo_root=repo_root),
        dependency=_relative_path(path=dependency.dependency, repo_root=repo_root),
        kind=dependency.kind,
        answer=answer,
        pattern=dependency.pattern,
        recursive=dependency.recursive,
    )


def _relative_path(*, path: Path, repo_root: Path) -> Path:
    if not path.is_absolute():
        parsed: PurePosixPath = PurePosixPath(path.as_posix())
        if any(part in {CURRENT_PATH_PART, PARENT_PATH_PART} for part in parsed.parts):
            raise RuleHarnessError(f"Rule emitted an escaping relative path: {path}.")
        return Path(parsed.as_posix())
    try:
        relative: Path = path.resolve().relative_to(repo_root.resolve())
    except ValueError as error:
        raise RuleHarnessError(
            "Rule results and project queries must remain inside the synthetic repository."
        ) from error
    return Path(relative.as_posix())
