"""Check expected Strata skill installations authoritatively or by fingerprints."""

from __future__ import annotations

from strata.agentdocs._helpers.freshness import inspect_skill_content
from strata.agentdocs._helpers.ownership import owned_skill_content
from strata.agentdocs.main.generate import generate_skill
from strata.agentdocs.models import (
    SkillFreshnessIssue,
    SkillFreshnessResult,
    SkillInstallPlan,
    SkillInstallTarget,
)
from strata.agentdocs.types import SkillFreshnessReason


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
    return SkillFreshnessResult(
        inspected_paths=tuple(target.path for target in targets),
        issues=tuple(issues),
    )
