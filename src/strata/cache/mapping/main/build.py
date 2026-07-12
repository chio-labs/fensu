"""Build a call map through persistent declaration metadata."""

from pathlib import Path

from strata.cache.mapping.helpers.evaluation import evaluate_cached_map
from strata.cache.mapping.models import CachedCallMap
from strata.cache.storage.main.build_store import build_cache_store
from strata.mapping.models import MappingSource


def build_cached_call_map(
    *, sources: tuple[MappingSource, ...], symbol: str, depth: int, repo_root: Path
) -> CachedCallMap:
    """Build one lazy call map with disposable persistent metadata."""

    return evaluate_cached_map(
        sources=sources,
        symbol=symbol,
        depth=depth,
        repo_root=repo_root,
        store=build_cache_store(repo_root=repo_root),
    )
