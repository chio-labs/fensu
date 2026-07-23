"""Filesystem and subprocess helpers for CLI end-to-end tests."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tomllib
from functools import partial
from pathlib import Path
from typing import cast

from fensu.cache.results.constants import CACHE_CHECK_OUTPUT_KIND, CACHE_FILE_RESULT_KIND
from fensu.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from tests.e2e.src.fensu.cli.main._test_types import (
    CliProjectFile,
    ConfigurableLayoutCliTestCase,
)

_EXECUTABLE_NAMES: dict[str, str] = {"nt": "fensu.exe", "posix": "fensu"}
_GENERATED_SNAPSHOT_PATHS: frozenset[str] = frozenset({".gitignore"})
_SITE_PACKAGES_DIRECTORIES: dict[str, str] = {
    "nt": "Lib/site-packages",
    "posix": "lib/python3.12/site-packages",
}
_CUSTOM_RULE_OPTION_SOURCE: str = """from __future__ import annotations

import ast

from fensu import Family, Fault, RuleContext, RuleOption, rule

_LIMIT = RuleOption.integer(name="limit", default=1, minimum=1, maximum=3)
_REQUIRED_PATH = RuleOption.string(name="required_path", default="policy.marker")


@rule(
    code="XOP001",
    family=Family.CUSTOM,
    slug="configured-limit",
    message="configured finding",
    cacheable=True,
    options=(_LIMIT, _REQUIRED_PATH),
)
def configured_limit(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    required_path = ctx.repo_root / ctx.option(_REQUIRED_PATH)
    if not ctx.project.exists(requester=ctx.path, path=required_path):
        return []
    return [
        ctx.fault(node=node, message=f"configured finding limit={ctx.option(_LIMIT)}")
        for node in module.body[:ctx.option(_LIMIT)]
    ]
"""


def installed_fensu_executable() -> Path:
    """Return the platform-specific native executable beside the active Python."""

    return Path(sys.executable).with_name(_EXECUTABLE_NAMES[os.name])


def isolated_site_packages(prefix: Path) -> Path:
    """Return the platform-specific site-packages directory for an isolated prefix."""

    return prefix / _SITE_PACKAGES_DIRECTORIES[os.name]


def run_configurable_layout_case(
    *, root: Path, test_case: ConfigurableLayoutCliTestCase
) -> subprocess.CompletedProcess[str]:
    """Write a complete project and run the installed Fensu console command."""

    (root / "fensu.toml").write_text(test_case.config, encoding="utf-8")
    for file in test_case.files:
        path: Path = root / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.source, encoding="utf-8")
    working_directory: Path = root / test_case.working_directory
    working_directory.mkdir(parents=True, exist_ok=True)
    environment: dict[str, str] = dict(os.environ)
    environment["NO_COLOR"] = "1"
    return subprocess.run(
        (str(installed_fensu_executable()), *test_case.argv),
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
        (str(installed_fensu_executable()), "check", "--no-color", *argv),
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def run_cli_terminal_check(*, root: Path, argv: tuple[str, ...]) -> tuple[int, str]:
    """Run an installed check with stdout and stderr attached to a pseudo-terminal."""

    master, slave = os.openpty()
    environment: dict[str, str] = dict(os.environ)
    environment.pop("NO_COLOR", None)
    process: subprocess.Popen[bytes] = subprocess.Popen(
        (str(installed_fensu_executable()), "check", *argv),
        cwd=root,
        env=environment,
        stdout=slave,
        stderr=slave,
    )
    os.close(slave)
    chunks: list[bytes] = []
    try:
        while chunk := os.read(master, 4096):
            chunks.append(chunk)
    except OSError:
        pass
    finally:
        os.close(master)
    return process.wait(), b"".join(chunks).decode()


def run_cli_init(
    *, root: Path, argv: tuple[str, ...], input_text: str
) -> subprocess.CompletedProcess[str]:
    """Run installed-console init with captured non-TTY standard streams."""

    environment: dict[str, str] = dict(os.environ)
    environment["NO_COLOR"] = "1"
    return subprocess.run(
        (str(installed_fensu_executable()), "init", *argv),
        cwd=root,
        env=environment,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def write_project_files(*, root: Path, files: tuple[CliProjectFile, ...]) -> None:
    """Write repository fixture files for an installed-console invocation."""

    for file in files:
        path: Path = root / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.source, encoding="utf-8")


def repository_text_snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    """Return every user-authored repository text file in deterministic order."""

    files: filter[Path] = filter(Path.is_file, sorted(root.rglob("*")))
    paths: filter[Path] = filter(partial(_is_user_authored_file, root=root), files)
    return tuple(
        (path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")) for path in paths
    )


def _is_user_authored_file(path: Path, *, root: Path) -> bool:
    relative_path: str = path.relative_to(root).as_posix()
    return relative_path not in _GENERATED_SNAPSHOT_PATHS and not relative_path.startswith(
        ".fensu/cache/"
    )


def config_values(root: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Parse generated config and return its ordered list-valued settings."""

    path: Path = root / "fensu.toml"
    try:
        parsed: dict[str, object] = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ()
    keys: filter[str] = filter(parsed.__contains__, ("roots", "tests", "tooling", "select"))
    return tuple((key, tuple(cast("list[str]", parsed[key]))) for key in keys)


def write_cli_project(
    *,
    root: Path,
    config: str,
    files: tuple[tuple[str, str], ...],
) -> None:
    """Write a complete installed-console cache fixture project."""

    (root / "fensu.toml").write_text(config, encoding="utf-8")
    for relative_path, source in files:
        path: Path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def write_custom_rule_option_project(*, root: Path) -> None:
    """Write a cacheable discovered custom rule with typed options and an existing dependency."""

    write_cli_project(
        root=root,
        config=(
            'roots = ["src/pkg"]\n'
            "tests = []\n"
            "tooling = []\n"
            'select = ["XOP001"]\n'
            'rule_paths = ["rules/custom.py"]\n'
        ),
        files=(
            ("src/pkg/alpha.py", "FIRST: int = 1\nSECOND: int = 2\n"),
            ("src/pkg/beta.py", "FIRST: int = 1\nSECOND: int = 2\n"),
            ("rules/custom.py", _CUSTOM_RULE_OPTION_SOURCE),
            ("policy.marker", "present\n"),
        ),
    )


def cache_snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    """Return deterministic logical cache keys and canonical record bytes."""

    database: Path = root / CACHE_DATABASE_RELATIVE_PATH
    try:
        with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as connection:
            rows: list[tuple[str, bytes]] = connection.execute(
                "SELECT key, data FROM records ORDER BY key"
            ).fetchall()
    except sqlite3.OperationalError:
        return ()
    return tuple(rows)


def corrupt_result_cache_record(root: Path) -> str:
    """Replace one canonical result envelope with malformed bytes."""

    database: Path = root / CACHE_DATABASE_RELATIVE_PATH
    with sqlite3.connect(database) as connection:
        row: tuple[str] | None = connection.execute(
            "SELECT key FROM records WHERE kind = ? ORDER BY key LIMIT 1",
            (CACHE_FILE_RESULT_KIND,),
        ).fetchone()
        assert row is not None, "cache contains no file-result record"
        key: str = row[0]
        connection.execute("UPDATE records SET data = ? WHERE key = ?", (b"{", key))
    return key


def remove_check_output_record(root: Path) -> int:
    """Delete the stored rendered-output surface and return removed row count."""

    database: Path = root / CACHE_DATABASE_RELATIVE_PATH
    with sqlite3.connect(database) as connection:
        cursor: sqlite3.Cursor = connection.execute(
            "DELETE FROM records WHERE kind = ?",
            (CACHE_CHECK_OUTPUT_KIND,),
        )
    return cursor.rowcount


def native_exec_trace(
    *, root: Path, argv: tuple[str, ...], trace_path: Path
) -> subprocess.CompletedProcess[str]:
    """Run the installed binary under OS exec accounting."""

    return subprocess.run(
        (
            shutil.which("strace") or "strace",
            "-f",
            "-e",
            "trace=execve",
            "-o",
            str(trace_path),
            str(installed_fensu_executable()),
            *argv,
        ),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def exec_trace_lines(trace_path: Path) -> tuple[str, ...]:
    """Return process-exec events from one strace output file."""

    lines: list[str] = trace_path.read_text(encoding="utf-8").splitlines()
    return tuple(filter(lambda line: "execve(" in line, lines))
