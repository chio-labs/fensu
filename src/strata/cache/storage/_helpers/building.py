"""Construct persistent cache storage implementations."""

from pathlib import Path

from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.types import CacheStorage


def create_cache_store(*, repo_root: Path) -> CacheStorage:
    """Return the active repository-local storage implementation."""

    return CacheStore(repo_root=repo_root)
