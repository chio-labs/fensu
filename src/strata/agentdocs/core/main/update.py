"""Install repository-aware Strata skill files."""

from __future__ import annotations

from pathlib import Path

from strata.agentdocs.core.helpers.installation import build_install_targets, write_skill_file
from strata.agentdocs.core.main.generate import generate_skill
from strata.agentdocs.core.models import SkillInstallTarget, SkillUpdateResult
from strata.agentdocs.core.types import SkillTarget
from strata.config.core.models import Config
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
    written_paths: list[Path] = []
    for install_target in install_targets:
        write_skill_file(path=install_target.path, content=content, force=force)
        written_paths.append(install_target.path)
    return SkillUpdateResult(written_paths=tuple(written_paths))
