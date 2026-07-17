"""Install repository-aware Strata skill files."""

from __future__ import annotations

from pathlib import Path

from strata.agentdocs._helpers.installation import write_skill_files
from strata.agentdocs._helpers.ownership import owned_skill_content
from strata.agentdocs.main._generate import generate_skill
from strata.agentdocs.main.build_install_plan import build_install_plan
from strata.agentdocs.models import (
    SkillGenerationContext,
    SkillInstallPlan,
    SkillUpdateResult,
)
from strata.agentdocs.types import SkillTarget


def update_skills(
    *,
    context: SkillGenerationContext,
    global_install: bool = False,
    requested_targets: tuple[SkillTarget, ...] = (),
    force: bool = False,
    home_dir: Path | None = None,
) -> SkillUpdateResult:
    """Generate and install Strata guidance for the active repository rules."""

    plan: SkillInstallPlan = build_install_plan(
        context=context,
        requested_targets=requested_targets,
        global_install=global_install,
        home_dir=home_dir,
    )
    content: str = owned_skill_content(context=context, content=generate_skill(context=context))
    written_paths: tuple[Path, ...] = tuple(target.path for target in plan.targets)
    write_skill_files(
        paths=written_paths,
        deletion_paths=plan.legacy_paths,
        content=content,
        force=force,
        owner=plan.owner,
    )
    return SkillUpdateResult(written_paths=written_paths)
