"""Public project-resolution entry point for call mapping."""

from __future__ import annotations

from pathlib import Path

from strata.mapping.helpers.project import resolve_mapping_project as _resolve_mapping_project
from strata.mapping.models import MappingProject


def resolve_mapping_project(*, cwd: Path, explicit_roots: tuple[str, ...]) -> MappingProject:
    """Resolve configured, explicit, or inferred sources for call mapping."""

    return _resolve_mapping_project(cwd=cwd, explicit_roots=explicit_roots)
