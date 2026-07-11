"""Build repository-local persistent cache storage."""

from pathlib import Path

from strata.cache.storage.helpers.building import create_cache_store
from strata.cache.storage.types import CacheStorage


def build_cache_store(*, repo_root: Path) -> CacheStorage:
    """Return storage bound to a repository without creating directories."""

    return create_cache_store(repo_root=repo_root)
