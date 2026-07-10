"""Resolve agent skill destinations and write generated files safely."""

from __future__ import annotations

from pathlib import Path

from strata.agentdocs.core.constants import GENERATED_MARKER, SKILL_NAME
from strata.agentdocs.core.exceptions import SkillInstallError
from strata.agentdocs.core.models import SkillInstallTarget
from strata.agentdocs.core.types import SkillTarget


def build_install_targets(
    *,
    project_dir: Path,
    requested_targets: tuple[SkillTarget, ...],
    global_install: bool,
    home_dir: Path | None,
) -> tuple[SkillInstallTarget, ...]:
    """Resolve requested or default agent-specific skill paths."""

    target_names: tuple[SkillTarget, ...] = requested_targets or tuple(SkillTarget)
    home_path: Path = home_dir if home_dir is not None else Path.home()
    install_targets: list[SkillInstallTarget] = []
    for target_name in target_names:
        if target_name is SkillTarget.OPENCODE:
            base_path: Path = (
                home_path / ".config/opencode" if global_install else project_dir / ".opencode"
            )
        elif target_name is SkillTarget.CLAUDE:
            base_path = home_path / ".claude" if global_install else project_dir / ".claude"
        else:
            base_path = home_path / ".agents" if global_install else project_dir / ".agents"
        install_targets.append(
            SkillInstallTarget(
                name=target_name,
                path=base_path / "skills" / SKILL_NAME / "SKILL.md",
            )
        )
    return tuple(install_targets)


def write_skill_file(*, path: Path, content: str, force: bool) -> None:
    """Write generated skill content without replacing user-authored files by default."""

    if path.exists():
        existing_content: str = path.read_text(encoding="utf-8")
        if GENERATED_MARKER not in existing_content and not force:
            raise SkillInstallError(
                f"refusing to overwrite non-generated skill file: {path}; rerun with --force"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
