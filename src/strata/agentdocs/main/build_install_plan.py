"""Build the pure expected Strata skill installation plan."""

from __future__ import annotations

from pathlib import Path

from strata.agentdocs._helpers.installation import build_install_targets, build_legacy_paths
from strata.agentdocs._helpers.ownership import skill_input_fingerprint, skill_owner_key
from strata.agentdocs.exceptions import SkillInstallError
from strata.agentdocs.models import (
    ProjectSkillBundle,
    ProjectSkillInstallTarget,
    SkillGenerationContext,
    SkillInstallPlan,
    SkillInstallTarget,
)
from strata.agentdocs.types import SkillTarget


def build_install_plan(
    *,
    context: SkillGenerationContext,
    global_install: bool = False,
    requested_targets: tuple[SkillTarget, ...] = (),
    home_dir: Path | None = None,
    project_bundles: tuple[ProjectSkillBundle, ...] | None = None,
) -> SkillInstallPlan:
    """Resolve expected targets and identities without reading or writing the filesystem."""

    install_targets: tuple[SkillInstallTarget, ...] = build_install_targets(
        install_root=context.install_root,
        skill_name=context.identity,
        requested_targets=requested_targets,
        global_install=global_install,
        home_dir=home_dir,
    )
    synchronized_bundles: tuple[ProjectSkillBundle, ...] = project_bundles or ()
    normalized_identities: list[str] = [context.identity.casefold()]
    normalized_identities.extend(bundle.identity.casefold() for bundle in synchronized_bundles)
    if len(normalized_identities) != len(set(normalized_identities)):
        raise SkillInstallError("duplicate normalized identity across generated and project skills")
    resolved_project_targets: list[ProjectSkillInstallTarget] = []
    for target in install_targets:
        for bundle in synchronized_bundles:
            resolved_project_targets.append(
                ProjectSkillInstallTarget(
                    name=target.name,
                    path=target.path.parent.parent / bundle.identity,
                    bundle=bundle,
                )
            )
    project_targets: tuple[ProjectSkillInstallTarget, ...] = tuple(resolved_project_targets)
    roots: tuple[Path, ...] = (
        context.project_root,
        *((context.git_root,) if context.git_root is not None else ()),
        context.install_root,
    )
    return SkillInstallPlan(
        context=context,
        targets=install_targets,
        project_targets=project_targets,
        legacy_paths=build_legacy_paths(
            context_roots=roots,
            install_targets=install_targets,
            global_install=global_install,
        ),
        owner=skill_owner_key(context),
        input_fingerprint=skill_input_fingerprint(context),
        synchronize_project_skills=project_bundles is not None,
    )
