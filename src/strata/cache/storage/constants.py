"""Persistent cache schema and location constants."""

import os
from pathlib import Path

CACHE_SCHEMA_VERSION: int = 1
CACHE_ROOT_RELATIVE_PATH: Path = Path(".strata/cache")
CACHE_VERSION_DIRECTORY_NAME: str = f"v{CACHE_SCHEMA_VERSION}"
CACHE_VERSION_RELATIVE_PATH: Path = CACHE_ROOT_RELATIVE_PATH / CACHE_VERSION_DIRECTORY_NAME
CACHE_RECORD_KIND_KEY: str = "kind"
CACHE_RECORD_PAYLOAD_KEY: str = "payload"
CACHE_RECORD_SCHEMA_KEY: str = "schema_version"
CACHE_RECORD_KEYS: frozenset[str] = frozenset(
    {CACHE_RECORD_KIND_KEY, CACHE_RECORD_PAYLOAD_KEY, CACHE_RECORD_SCHEMA_KEY}
)
PARENT_PATH_PART: str = ".."
CACHE_FILE_MODE: int = 0o600
CACHE_TEMPORARY_SUFFIX: str = ".tmp"
_directory_flag: int = getattr(os, "O_DIRECTORY", 0)
_no_follow_flag: int = getattr(os, "O_NOFOLLOW", 0)
_nonblocking_flag: int = getattr(os, "O_NONBLOCK", 0)
DIRECTORY_OPEN_FLAGS: int = os.O_RDONLY | _directory_flag | _no_follow_flag
FILE_READ_FLAGS: int = os.O_RDONLY | _no_follow_flag | _nonblocking_flag
FILE_WRITE_FLAGS: int = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _no_follow_flag
SECURE_CACHE_IO_SUPPORTED: bool = bool(
    _directory_flag
    and _no_follow_flag
    and os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and os.unlink in os.supports_dir_fd
    and os.rename in os.supports_dir_fd
)
