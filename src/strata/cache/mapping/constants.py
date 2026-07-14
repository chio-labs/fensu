"""Persistent call-map cache constants."""

from pathlib import Path

MAP_CACHE_CONTRACT_VERSION: int = 2
MAP_FILE_RECORD_KIND: str = "map-file-declarations-v2"
MAP_MANIFEST_RECORD_KIND: str = "map-project-manifest-v2"
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
        "protocol_implementations",
        "record_fingerprint",
    }
)
MAP_FILE_KEYS: frozenset[str] = frozenset(
    {"classes", "functions", "identity", "module_name", "path", "record_fingerprint"}
)
MAP_CLASS_KEYS: frozenset[str] = frozenset({"base_keys", "key", "protocol"})
MAP_FUNCTION_KEYS: frozenset[str] = frozenset({"key", "name", "owning_class", "qualified_name"})
