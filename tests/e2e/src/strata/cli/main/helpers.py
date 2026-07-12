"""Filesystem and subprocess helpers for CLI end-to-end tests."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from strata.cache.results.constants import CACHE_FILE_RESULT_KIND
from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from tests.e2e.src.strata.cli.main._test_types import ConfigurableLayoutCliTestCase


def run_configurable_layout_case(
    *, root: Path, test_case: ConfigurableLayoutCliTestCase
) -> subprocess.CompletedProcess[str]:
    """Write a complete project and run the installed Strata console command."""

    (root / "strata.toml").write_text(test_case.config, encoding="utf-8")
    for file in test_case.files:
        path: Path = root / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.source, encoding="utf-8")
    working_directory: Path = root / test_case.working_directory
    working_directory.mkdir(parents=True, exist_ok=True)
    environment: dict[str, str] = dict(os.environ)
    environment["NO_COLOR"] = "1"
    return subprocess.run(
        (str(Path(sys.executable).with_name("strata")), *test_case.argv),
        cwd=working_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def run_cli_check(*, root: Path, argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    """Run one installed-console check process in a prepared project."""

    environment: dict[str, str] = dict(os.environ)
    environment["NO_COLOR"] = "1"
    return subprocess.run(
        (str(Path(sys.executable).with_name("strata")), "check", "--no-color", *argv),
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def write_cli_project(
    *,
    root: Path,
    config: str,
    files: tuple[tuple[str, str], ...],
) -> None:
    """Write a complete installed-console cache fixture project."""

    (root / "strata.toml").write_text(config, encoding="utf-8")
    for relative_path, source in files:
        path: Path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def cache_snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    """Return deterministic logical cache keys and canonical record bytes."""

    database: Path = root / CACHE_DATABASE_RELATIVE_PATH
    if not database.is_file():
        return ()
    with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as connection:
        rows: list[tuple[str, bytes]] = connection.execute(
            "SELECT key, data FROM records ORDER BY key"
        ).fetchall()
    return tuple(rows)


def corrupt_result_cache_record(root: Path) -> str:
    """Replace one canonical result envelope with malformed bytes."""

    database: Path = root / CACHE_DATABASE_RELATIVE_PATH
    with sqlite3.connect(database) as connection:
        row: tuple[str] | None = connection.execute(
            "SELECT key FROM records WHERE kind = ? ORDER BY key LIMIT 1",
            (CACHE_FILE_RESULT_KIND,),
        ).fetchone()
        if row is None:
            raise AssertionError("cache contains no file-result record")
        key: str = row[0]
        connection.execute("UPDATE records SET data = ? WHERE key = ?", (b"{", key))
    return key
