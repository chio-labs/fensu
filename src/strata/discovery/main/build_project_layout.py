"""Public project-layout builder."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery._helpers.layout import build_project_layout as _build_project_layout
from strata.discovery.models import ProjectLayout, RepoRoot


def build_project_layout(*, config: Config, repo_root: RepoRoot) -> ProjectLayout:
    """Resolve and validate configured paths against one repository root."""

    return _build_project_layout(config=config, repo_root=repo_root)
