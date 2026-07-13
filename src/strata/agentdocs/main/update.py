"""Install repository-aware Strata skill files."""

from __future__ import annotations

from pathlib import Path

from strata.agentdocs._helpers.installation import (
    build_install_targets,
    write_skill_files,
)
from strata.agentdocs.main.generate import generate_skill
from strata.agentdocs.models import SkillInstallTarget, SkillUpdateResult
from strata.agentdocs.types import SkillTarget
from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec


def update_skills(
    *,
    config: Config,
    rules: tuple[RuleSpec, ...],
    project_dir: Path,
    global_install: bool = False,
    requested_targets: tuple[SkillTarget, ...] = (),
    force: bool = False,
    home_dir: Path | None = None,
) -> SkillUpdateResult:
    """Generate and install Strata guidance for the active repository rules."""

    content: str = generate_skill(config=config, rules=rules)
    install_targets: tuple[SkillInstallTarget, ...] = build_install_targets(
        project_dir=project_dir,
        requested_targets=requested_targets,
        global_install=global_install,
        home_dir=home_dir,
    )
    written_paths: tuple[Path, ...] = tuple(target.path for target in install_targets)
    write_skill_files(paths=written_paths, content=content, force=force)
    return SkillUpdateResult(written_paths=written_paths)
