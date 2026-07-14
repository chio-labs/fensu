"""Transactional repository-local SQLite cache storage."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from strata.cache.storage._helpers.serialization import decode_cache_record, encode_cache_record
from strata.cache.storage.constants import (
    CACHE_DATABASE_APPLICATION_ID,
    CACHE_DATABASE_BUSY_TIMEOUT_MS,
    CACHE_DATABASE_READ_CHUNK_SIZE,
    CACHE_DATABASE_RECORD_COLUMNS,
    CACHE_DATABASE_RELATIVE_PATH,
    CACHE_DATABASE_ROW_COLUMN_COUNT,
    CACHE_DATABASE_SCHEMA_VERSION,
    CACHE_DATABASE_SELECTED_COLUMN_COUNT,
    CACHE_DATABASE_WAL_MODE,
    PARENT_PATH_PART,
)
from strata.cache.storage.exceptions import CachePathError
from strata.cache.storage.models import (
    CacheMutation,
    CacheMutationOutcome,
    CacheRead,
    CacheRecord,
    CacheWrite,
)
from strata.cache.storage.types import CacheMutator

_CREATE_RECORDS_SQL: str = (
    "CREATE TABLE records ("
    "key TEXT PRIMARY KEY NOT NULL, "
    "kind TEXT NOT NULL, "
    "data BLOB NOT NULL"
    ") WITHOUT ROWID"
)
_READ_RECORDS_SQL_PREFIX: str = "SELECT key, kind, data FROM records WHERE key IN"
_UPSERT_RECORD_SQL: str = (
    "INSERT INTO records(key, kind, data) VALUES (?, ?, ?) "
    "ON CONFLICT(key) DO UPDATE SET kind = excluded.kind, data = excluded.data"
)
_SELECT_PREFIX_KEYS_SQL: str = "SELECT key FROM records WHERE key LIKE ?"
_DELETE_RECORDS_SQL_PREFIX: str = "DELETE FROM records WHERE key IN"


class CacheStore:
    """Store canonical records in one disposable transactional database."""

    def __init__(self, *, repo_root: Path) -> None:
        """Bind storage without creating the cache database."""

        self._repo_root: Path = repo_root.resolve()
        self._database: Path = self._repo_root / CACHE_DATABASE_RELATIVE_PATH

    @property
    def root(self) -> Path:
        """Return the active cache database path."""

        return self._database

    def read(self, *, relative_path: Path, expected_kind: str) -> CacheRecord | None:
        """Return a validated record or None for any unavailable cache state."""

        return self.read_batch(
            reads=(CacheRead(relative_path=relative_path, expected_kind=expected_kind),)
        )[0]

    def read_batch(self, *, reads: tuple[CacheRead, ...]) -> tuple[CacheRecord | None, ...]:
        """Read canonical records through one consistent database connection."""

        if not reads:
            return ()
        keyed_reads: tuple[tuple[str, str], ...] = tuple(
            (self._key(read.relative_path), read.expected_kind) for read in reads
        )
        misses: tuple[None, ...] = (None,) * len(reads)
        if not self._database_is_readable():
            return misses
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                f"{self._database.as_uri()}?mode=ro",
                uri=True,
                timeout=CACHE_DATABASE_BUSY_TIMEOUT_MS / 1_000,
            )
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            if not _database_identity_is_current(connection):
                return misses
            rows_by_key: dict[str, tuple[object, ...]] = _fetch_rows(
                connection=connection,
                keys=tuple(key for key, _ in keyed_reads),
            )
            return tuple(
                _decode_row(row=rows_by_key.get(key), expected_kind=expected_kind)
                for key, expected_kind in keyed_reads
            )
        except (OSError, RuntimeError, sqlite3.Error):
            return misses
        finally:
            _close_connection(connection)

    def write(self, *, relative_path: Path, record: CacheRecord) -> bool:
        """Publish one record in a transaction."""

        return self.write_batch(writes=(CacheWrite(relative_path=relative_path, record=record),))

    def write_batch(self, *, writes: tuple[CacheWrite, ...]) -> bool:
        """Commit every encoded record together or leave prior state unchanged."""

        if not writes:
            return True
        rows: tuple[tuple[str, str, bytes], ...] = self._encoded_rows(writes)
        connection: sqlite3.Connection | None = self._writable_connection()
        if connection is None:
            return False
        try:
            if not _begin_writable_transaction(connection):
                _rollback_connection(connection)
                return False
            connection.executemany(_UPSERT_RECORD_SQL, rows)
            connection.commit()
            return True
        except (OSError, RuntimeError, sqlite3.Error):
            _rollback_connection(connection)
            return False
        finally:
            _close_connection(connection)

    def mutate_batch(
        self,
        *,
        reads: tuple[CacheRead, ...],
        mutate: CacheMutator,
    ) -> CacheMutationOutcome:
        """Read, merge, publish, and sweep records in one exclusive transaction."""

        failed: CacheMutationOutcome = CacheMutationOutcome(published=False, mutation=None)
        keyed_reads: tuple[tuple[str, str], ...] = tuple(
            (self._key(read.relative_path), read.expected_kind) for read in reads
        )
        connection: sqlite3.Connection | None = self._writable_connection()
        if connection is None:
            return failed
        try:
            if not _begin_writable_transaction(connection):
                _rollback_connection(connection)
                return failed
            rows_by_key: dict[str, tuple[object, ...]] = _fetch_rows(
                connection=connection,
                keys=tuple(key for key, _ in keyed_reads),
            )
            records: tuple[CacheRecord | None, ...] = tuple(
                _decode_row(row=rows_by_key.get(key), expected_kind=expected_kind)
                for key, expected_kind in keyed_reads
            )
            mutation: CacheMutation | None = mutate(records)
            if mutation is None:
                _rollback_connection(connection)
                return CacheMutationOutcome(published=True, mutation=None)
            rows: tuple[tuple[str, str, bytes], ...] = self._encoded_rows(mutation.writes)
            connection.executemany(_UPSERT_RECORD_SQL, rows)
            if mutation.swept_prefix is not None:
                self._sweep_unreferenced(
                    connection=connection,
                    prefix=mutation.swept_prefix,
                    retained_paths=mutation.retained_paths,
                    written_keys=tuple(key for key, _, _ in rows),
                )
            connection.commit()
            return CacheMutationOutcome(published=True, mutation=mutation)
        except (OSError, RuntimeError, sqlite3.Error):
            _rollback_connection(connection)
            return failed
        finally:
            _close_connection(connection)

    def _writable_connection(self) -> sqlite3.Connection | None:
        if not self._prepare_database_parent():
            return None
        if self._database.exists() and not self._database_is_readable():
            return None
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                self._database,
                timeout=CACHE_DATABASE_BUSY_TIMEOUT_MS / 1_000,
                isolation_level=None,
            )
            connection.execute(f"PRAGMA busy_timeout = {CACHE_DATABASE_BUSY_TIMEOUT_MS}")
            journal_mode: tuple[object, ...] | None = connection.execute(
                "PRAGMA journal_mode = WAL"
            ).fetchone()
            if journal_mode is None or str(journal_mode[0]).lower() != CACHE_DATABASE_WAL_MODE:
                _close_connection(connection)
                return None
            connection.execute("PRAGMA synchronous = NORMAL")
            return connection
        except (OSError, RuntimeError, sqlite3.Error):
            _close_connection(connection)
            return None

    def _sweep_unreferenced(
        self,
        *,
        connection: sqlite3.Connection,
        prefix: Path,
        retained_paths: tuple[Path, ...],
        written_keys: tuple[str, ...],
    ) -> None:
        self._validate_relative_path(prefix)
        retained: frozenset[str] = frozenset(
            self._key(path) for path in retained_paths
        ) | frozenset(written_keys)
        rows: tuple[tuple[object, ...], ...] = tuple(
            connection.execute(_SELECT_PREFIX_KEYS_SQL, (f"{prefix.as_posix()}/%",)).fetchall()
        )
        doomed: tuple[str, ...] = tuple(
            row[0] for row in rows if isinstance(row[0], str) and row[0] not in retained
        )
        for offset in range(0, len(doomed), CACHE_DATABASE_READ_CHUNK_SIZE):
            chunk: tuple[str, ...] = doomed[offset : offset + CACHE_DATABASE_READ_CHUNK_SIZE]
            placeholders: str = ",".join("?" for _ in chunk)
            connection.execute(f"{_DELETE_RECORDS_SQL_PREFIX} ({placeholders})", chunk)

    def _encoded_rows(self, writes: tuple[CacheWrite, ...]) -> tuple[tuple[str, str, bytes], ...]:
        keys: set[str] = set()
        rows: list[tuple[str, str, bytes]] = []
        for write in writes:
            key: str = self._key(write.relative_path)
            if key in keys:
                raise CachePathError(f"Cache publication contains duplicate key: {key}")
            keys.add(key)
            encoded: bytes = (
                write.encoded if write.encoded is not None else encode_cache_record(write.record)
            )
            rows.append((key, write.record.kind, encoded))
        return tuple(rows)

    def _key(self, relative_path: Path) -> str:
        self._validate_relative_path(relative_path)
        return relative_path.as_posix()

    def _validate_relative_path(self, relative_path: Path) -> None:
        if (
            relative_path.is_absolute()
            or not relative_path.parts
            or PARENT_PATH_PART in relative_path.parts
        ):
            raise CachePathError(
                f"Cache entry path must stay below the cache root: {relative_path}"
            )

    def _prepare_database_parent(self) -> bool:
        current: Path = self._repo_root
        try:
            for part in CACHE_DATABASE_RELATIVE_PATH.parent.parts:
                current = current / part
                if current.exists():
                    if current.is_symlink() or not current.is_dir():
                        return False
                    continue
                try:
                    current.mkdir()
                except FileExistsError:
                    if current.is_symlink() or not current.is_dir():
                        return False
        except (OSError, RuntimeError):
            return False
        return True

    def _database_is_readable(self) -> bool:
        try:
            return (
                self._database.is_file()
                and not self._database.is_symlink()
                and self._parents_are_directories()
            )
        except (OSError, RuntimeError):
            return False

    def _parents_are_directories(self) -> bool:
        current: Path = self._repo_root
        for part in CACHE_DATABASE_RELATIVE_PATH.parent.parts:
            current = current / part
            if current.is_symlink() or not current.is_dir():
                return False
        return True


def _begin_writable_transaction(connection: sqlite3.Connection) -> bool:
    connection.execute("BEGIN IMMEDIATE")
    if _database_is_uninitialized(connection):
        connection.execute(_CREATE_RECORDS_SQL)
        connection.execute(f"PRAGMA application_id = {CACHE_DATABASE_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {CACHE_DATABASE_SCHEMA_VERSION}")
        return True
    return _database_identity_is_current(connection)


def _fetch_rows(
    *,
    connection: sqlite3.Connection,
    keys: tuple[str, ...],
) -> dict[str, tuple[object, ...]]:
    rows_by_key: dict[str, tuple[object, ...]] = {}
    for offset in range(0, len(keys), CACHE_DATABASE_READ_CHUNK_SIZE):
        chunk: tuple[str, ...] = keys[offset : offset + CACHE_DATABASE_READ_CHUNK_SIZE]
        placeholders: str = ",".join("?" for _ in chunk)
        rows: tuple[tuple[object, ...], ...] = tuple(
            connection.execute(f"{_READ_RECORDS_SQL_PREFIX} ({placeholders})", chunk).fetchall()
        )
        for row in rows:
            if len(row) == CACHE_DATABASE_SELECTED_COLUMN_COUNT and isinstance(row[0], str):
                rows_by_key[row[0]] = row[1:]
    return rows_by_key


def _database_identity_is_current(connection: sqlite3.Connection) -> bool:
    application_id: tuple[object, ...] | None = connection.execute(
        "PRAGMA application_id"
    ).fetchone()
    user_version: tuple[object, ...] | None = connection.execute("PRAGMA user_version").fetchone()
    columns: tuple[tuple[object, ...], ...] = tuple(
        connection.execute("PRAGMA table_info(records)").fetchall()
    )
    column_identity: tuple[tuple[object, ...], ...] = tuple(
        (column[1], column[2], column[3], column[5]) for column in columns
    )
    return (
        application_id == (CACHE_DATABASE_APPLICATION_ID,)
        and user_version == (CACHE_DATABASE_SCHEMA_VERSION,)
        and column_identity == CACHE_DATABASE_RECORD_COLUMNS
    )


def _decode_row(*, row: tuple[object, ...] | None, expected_kind: str) -> CacheRecord | None:
    if row is None or len(row) != CACHE_DATABASE_ROW_COLUMN_COUNT:
        return None
    kind, data = row
    if kind != expected_kind or not isinstance(data, bytes):
        return None
    return decode_cache_record(data=data, expected_kind=expected_kind)


def _database_is_uninitialized(connection: sqlite3.Connection) -> bool:
    application_id: tuple[object, ...] | None = connection.execute(
        "PRAGMA application_id"
    ).fetchone()
    user_version: tuple[object, ...] | None = connection.execute("PRAGMA user_version").fetchone()
    tables: tuple[tuple[object, ...], ...] = tuple(
        connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    )
    return application_id == (0,) and user_version == (0,) and not tables


def _rollback_connection(connection: sqlite3.Connection | None) -> None:
    try:
        if connection is not None:
            connection.rollback()
    except sqlite3.Error:
        return


def _close_connection(connection: sqlite3.Connection | None) -> None:
    try:
        if connection is not None:
            connection.close()
    except sqlite3.Error:
        return
