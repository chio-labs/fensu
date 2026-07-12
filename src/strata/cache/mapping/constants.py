"""Persistent call-map cache constants."""

from pathlib import Path

MAP_CACHE_CONTRACT_VERSION: int = 1
MAP_FILE_RECORD_KIND: str = "map-file-declarations-v1"
MAP_MANIFEST_RECORD_KIND: str = "map-project-manifest-v1"
MAP_CACHE_PREFIX: Path = Path("mapping")
MAP_FILE_PREFIX: Path = MAP_CACHE_PREFIX / "files"
MAP_MANIFEST_PATH: Path = MAP_CACHE_PREFIX / "manifest"
MAP_MANIFEST_KEYS: frozenset[str] = frozenset(
    {
        "bare_functions",
        "classes",
        "files",
        "functions",
        "input_fingerprint",
        "record_fingerprint",
    }
)
MAP_FILE_KEYS: frozenset[str] = frozenset(
    {"class_keys", "functions", "identity", "module_name", "path", "record_fingerprint"}
)
MAP_FUNCTION_KEYS: frozenset[str] = frozenset({"key", "name", "owning_class", "qualified_name"})
