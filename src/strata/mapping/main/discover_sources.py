"""Discover immutable mapping source snapshots."""

from pathlib import Path

from strata.mapping.helpers.index import discover_source_snapshots
from strata.mapping.models import MappingSource, SourceSnapshot


def discover_mapping_sources(
    *, sources: tuple[MappingSource, ...], repo_root: Path
) -> tuple[SourceSnapshot, ...]:
    """Discover and read every selected source exactly once."""

    return discover_source_snapshots(sources=sources, repo_root=repo_root)
