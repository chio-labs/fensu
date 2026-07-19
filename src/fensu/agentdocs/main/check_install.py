"""Check expected Fensu skill installations authoritatively or by fingerprints."""

from __future__ import annotations

from pathlib import Path

from fensu.agentdocs._helpers.freshness import (
    inspect_project_skill_install,
    inspect_skill_content,
)
from fensu.agentdocs._helpers.ownership import owned_skill_content
from fensu.agentdocs.main._generate import generate_skill
from fensu.agentdocs.models import (
    SkillFreshnessIssue,
    SkillFreshnessResult,
    SkillInstallPlan,
    SkillInstallTarget,
)
from fensu.agentdocs.types import SkillFreshnessReason


def check_skill_install(*, plan: SkillInstallPlan, authoritative: bool) -> SkillFreshnessResult:
    """Inspect only planned targets, rendering bytes solely for authoritative checks."""

    expected_content: bytes | None = None
    if authoritative:
        generated: str = generate_skill(context=plan.context)
        expected_content = owned_skill_content(context=plan.context, content=generated).encode(
            "utf-8"
        )
    targets: tuple[SkillInstallTarget, ...] = tuple(
        sorted(plan.targets, key=lambda target: target.path.as_posix())
    )
    issues: list[SkillFreshnessIssue] = []
    for target in targets:
        reason: SkillFreshnessReason | None = inspect_skill_content(
            plan=plan,
            path=target.path,
            expected_content=expected_content,
        )
        if reason is not None:
            issues.append(SkillFreshnessIssue(path=target.path, reason=reason))
    if authoritative:
        issues.extend(inspect_project_skill_install(plan))
    inspected: list[Path] = [target.path for target in targets]
    for target in plan.project_targets:
        for file in target.bundle.files:
            inspected.append(target.path / file.relative_path)
    inspected_paths: tuple[Path, ...] = tuple(inspected)
    return SkillFreshnessResult(
        inspected_paths=tuple(sorted(inspected_paths, key=lambda path: path.as_posix())),
        issues=tuple(sorted(issues, key=lambda issue: issue.path.as_posix())),
    )
