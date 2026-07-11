"""Persistent cache schema and location constants."""

from pathlib import Path

CACHE_SCHEMA_VERSION: int = 1
CACHE_ROOT_RELATIVE_PATH: Path = Path(".strata/cache")
CACHE_VERSION_DIRECTORY_NAME: str = f"v{CACHE_SCHEMA_VERSION}"
CACHE_VERSION_RELATIVE_PATH: Path = CACHE_ROOT_RELATIVE_PATH / CACHE_VERSION_DIRECTORY_NAME
