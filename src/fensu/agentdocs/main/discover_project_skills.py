"""Discover canonical active project skill bundles independently of memory."""

from __future__ import annotations

from pathlib import Path

from fensu.agentdocs._helpers.installation import discover_canonical_project_skills
from fensu.agentdocs.models import ProjectSkillBundle


def discover_project_skills(
    *, project_root: Path, generated_identity: str
) -> tuple[ProjectSkillBundle, ...]:
    """Capture every canonical active project skill as a safe immutable bundle."""

    return discover_canonical_project_skills(
        project_root=project_root,
        generated_identity=generated_identity,
    )
