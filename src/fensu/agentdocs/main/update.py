"""Install repository-aware Fensu skill files."""

from __future__ import annotations

from pathlib import Path

from fensu.agentdocs._helpers.installation import write_skill_installation
from fensu.agentdocs._helpers.ownership import owned_skill_content
from fensu.agentdocs.main._generate import generate_skill
from fensu.agentdocs.main.build_install_plan import build_install_plan
from fensu.agentdocs.models import (
    ProjectSkillBundle,
    SkillGenerationContext,
    SkillInstallPlan,
    SkillUpdateResult,
)
from fensu.agentdocs.types import SkillTarget


def update_skills(
    *,
    context: SkillGenerationContext,
    global_install: bool = False,
    requested_targets: tuple[SkillTarget, ...] = (),
    force: bool = False,
    home_dir: Path | None = None,
    project_bundles: tuple[ProjectSkillBundle, ...] | None = None,
) -> SkillUpdateResult:
    """Generate and install Fensu guidance for the active repository rules."""

    plan: SkillInstallPlan = build_install_plan(
        context=context,
        requested_targets=requested_targets,
        global_install=global_install,
        home_dir=home_dir,
        project_bundles=project_bundles,
    )
    content: str = owned_skill_content(context=context, content=generate_skill(context=context))
    resolved_project_paths: list[Path] = []
    for target in plan.project_targets:
        for file in target.bundle.files:
            resolved_project_paths.append(target.path / file.relative_path)
    project_paths: tuple[Path, ...] = tuple(resolved_project_paths)
    written_paths: tuple[Path, ...] = (
        *(target.path for target in plan.targets),
        *project_paths,
    )
    write_skill_installation(
        plan=plan,
        generated_content=content.encode("utf-8"),
        force=force,
    )
    return SkillUpdateResult(written_paths=written_paths)
