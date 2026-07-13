"""Build the pure expected Strata skill installation plan."""

from __future__ import annotations

from pathlib import Path

from strata.agentdocs._helpers.installation import build_install_targets, build_legacy_paths
from strata.agentdocs._helpers.ownership import skill_input_fingerprint, skill_owner_key
from strata.agentdocs.models import SkillGenerationContext, SkillInstallPlan, SkillInstallTarget
from strata.agentdocs.types import SkillTarget


def build_install_plan(
    *,
    context: SkillGenerationContext,
    global_install: bool = False,
    requested_targets: tuple[SkillTarget, ...] = (),
    home_dir: Path | None = None,
) -> SkillInstallPlan:
    """Resolve expected targets and identities without reading or writing the filesystem."""

    install_targets: tuple[SkillInstallTarget, ...] = build_install_targets(
        install_root=context.install_root,
        skill_name=context.identity,
        requested_targets=requested_targets,
        global_install=global_install,
        home_dir=home_dir,
    )
    roots: tuple[Path, ...] = (
        context.project_root,
        *((context.git_root,) if context.git_root is not None else ()),
        context.install_root,
    )
    return SkillInstallPlan(
        context=context,
        targets=install_targets,
        legacy_paths=build_legacy_paths(
            context_roots=roots,
            install_targets=install_targets,
            global_install=global_install,
        ),
        owner=skill_owner_key(context),
        input_fingerprint=skill_input_fingerprint(context),
    )
