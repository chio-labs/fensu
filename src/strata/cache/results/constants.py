"""Persistent evaluation-result record constants."""

from pathlib import Path

CACHE_METADATA_KIND: str = "metadata"
CACHE_INDEX_KIND: str = "index"
CACHE_FILE_RESULT_KIND: str = "file_result"
CACHE_FACT_KIND: str = "fact"
CACHE_METADATA_PATH: Path = Path("metadata.json")
CACHE_INDEX_PATH: Path = Path("index.json")
CACHE_RESULTS_DIRECTORY: Path = Path("results")
CACHE_JSON_SUFFIX: str = ".json"
FINGERPRINT_DIRECTORY_PREFIX_LENGTH: int = 2
SHA256_HEX_LENGTH: int = 64
SHA256_HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdef")
WINDOWS_PATH_SEPARATOR: str = "\\"
PARENT_PATH_PART: str = ".."
REPOSITORY_ROOT_PATH: str = "."
CORE_RULE_CODE_PATTERN: str = r"SF[A-Z][0-9]{3}"
CUSTOM_RULE_CODE_PATTERN: str = r"X[A-Za-z0-9][A-Za-z0-9_-]*"
RULE_EXCEPTION_SYMBOL_PATTERN: str = r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?"
METADATA_PAYLOAD_KEYS: frozenset[str] = frozenset({"global_fingerprint"})
INDEX_PAYLOAD_KEYS: frozenset[str] = frozenset({"entries", "global_fingerprint"})
INDEX_ENTRY_KEYS: frozenset[str] = frozenset(
    {"path", "record_fingerprint", "result_fingerprint", "source_fingerprint"}
)
FILE_RESULT_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {"applied_exception_keys", "dependencies", "faults", "path", "source_fingerprint"}
)
FACT_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {"fact_kind", "path", "payload", "source_fingerprint"}
)
FAULT_KEYS: frozenset[str] = frozenset({"code", "column", "line", "message", "path", "remediation"})
RULE_EXCEPTION_KEY_KEYS: frozenset[str] = frozenset({"path", "rule", "symbol"})
DEPENDENCY_OBSERVATION_KEYS: frozenset[str] = frozenset(
    {
        "answer",
        "dependency_path",
        "kind",
        "pattern",
        "query_path",
        "recursive",
        "requester_path",
    }
)
