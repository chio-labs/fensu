"""Helpers for CLI tests."""

from __future__ import annotations

import sqlite3
from io import StringIO
from pathlib import Path

import pytest

from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH


class CaptureOutput(StringIO):
    """Small text sink with configurable terminal-color support."""

    def __init__(self, *, is_terminal: bool = False) -> None:
        super().__init__()
        self._is_terminal: bool = is_terminal

    def isatty(self) -> bool:
        return self._is_terminal


def configure_no_color(*, monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    """Set or clear the conventional terminal color opt-out."""

    monkeypatch.delenv("NO_COLOR", raising=False)
    if enabled:
        monkeypatch.setenv("NO_COLOR", "1")


def write_cli_fixture_project(
    *, root: Path, rule_code: str, include_core_rules: bool = False
) -> None:
    """Write a tiny project with one custom rule that always reports a fault."""

    (root / "src" / "pkg").mkdir(parents=True)
    (root / "rules").mkdir()
    (root / "src" / "pkg" / "target.py").write_text("value: int = 1\n", encoding="utf-8")
    selected_rules: str = f'"SF", "{rule_code}"' if include_core_rules else f'"{rule_code}"'
    ignored_rules: str = 'ignore = ["SFX002"]\n' if include_core_rules else ""
    config: str = (
        f'roots = ["src/pkg"]\nselect = [{selected_rules}]\n{ignored_rules}'
        'rule_paths = ["rules/custom_rule.py"]\n'
    )
    (root / "strata.toml").write_text(config, encoding="utf-8")
    (root / "rules" / "custom_rule.py").write_text(
        f'''
from __future__ import annotations

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="{rule_code}",
    family=Family.CUSTOM,
    slug="always",
    message="custom fault",
    remediation="apply the custom remediation",
)
def always(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return [ctx.fault(node=module.body[0])]
''',
        encoding="utf-8",
    )


def write_cli_no_fault_project(root: Path) -> None:
    """Write a tiny project with no selected rules."""

    source_dir: Path = root / "src" / "pkg" / "domain" / "core"
    source_dir.mkdir(parents=True)
    (source_dir / "constants.py").write_text("VALUE: int = 1\n", encoding="utf-8")
    (root / "strata.toml").write_text('roots = ["src/pkg"]\n', encoding="utf-8")


def write_cli_exception_project(root: Path) -> None:
    """Write a project whose only core fault is exactly excepted."""

    source: Path = root / "src" / "pkg" / "external.py"
    source.parent.mkdir(parents=True)
    source.write_text("def callback(value: int) -> None:\n    pass\n", encoding="utf-8")
    (root / "strata.toml").write_text(
        'roots = ["src/pkg"]\n'
        'select = ["SFS120"]\n'
        "[[rule_exceptions]]\n"
        'rule = "SFS120"\n'
        'path = "src/pkg/external.py"\n'
        'symbols = ["callback"]\n'
        'reason = "The external API invokes this callback positionally."\n',
        encoding="utf-8",
    )


def write_cli_stale_exception_project(root: Path) -> None:
    """Write a project whose valid exception no longer suppresses a fault."""

    write_cli_exception_project(root)
    source: Path = root / "src" / "pkg" / "external.py"
    source.write_text("def callback(*, value: int) -> None:\n    pass\n", encoding="utf-8")


def write_cli_core_fault_project(root: Path, *, cache_enabled: bool | None = None) -> None:
    """Write a cacheable project with one deterministic core fault."""

    source: Path = root / "src/pkg/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    cache_config: str = (
        "" if cache_enabled is None else f"[cache]\nenabled = {str(cache_enabled).lower()}\n"
    )
    (root / "strata.toml").write_text(
        f'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n{cache_config}',
        encoding="utf-8",
    )


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


def write_cli_map_project(
    *,
    root: Path,
    ambiguous: bool = False,
    cycle: bool = False,
    dynamic_seam: bool = False,
    configured_root: str = "src/pkg",
    write_config: bool = True,
    relative_imports: bool = False,
    dynamic_first: bool = False,
) -> None:
    """Write a project with a resolvable three-function call chain."""

    package: Path = root / configured_root
    package_name: str = package.name
    package.mkdir(parents=True)
    if write_config:
        (root / "strata.toml").write_text(f'roots = ["{configured_root}"]\n', encoding="utf-8")
    parameters: str = "callback: object" if dynamic_seam else ""
    callback_line: str = "    callback()" if dynamic_seam else ""
    step_import: str = (
        "from .steps import step" if relative_imports else f"from {package_name}.steps import step"
    )
    function_lines: tuple[str, ...] = ("    step()", callback_line)
    if dynamic_first:
        function_lines = (callback_line, "    step()")
    function_body: str = "\n".join(filter(None, function_lines))
    (package / "entry.py").write_text(
        (f"{step_import}\n\ndef run({parameters}) -> None:\n{function_body}\n"),
        encoding="utf-8",
    )
    finish_import: str = (
        "from . import finish as finishing"
        if relative_imports
        else f"import {package_name}.finish as finishing"
    )
    (package / "steps.py").write_text(
        f"{finish_import}\n\ndef step() -> None:\n    finishing.finish()\n",
        encoding="utf-8",
    )
    finish_source: str = "def finish() -> None:\n    return None\n"
    if cycle:
        finish_source = (
            f"from {package_name}.entry import run\n\ndef finish() -> None:\n    run()\n"
        )
    (package / "finish.py").write_text(finish_source, encoding="utf-8")
    if ambiguous:
        (package / "other.py").write_text("def run() -> None:\n    return None\n", encoding="utf-8")


def write_multi_root_map_project(root: Path) -> None:
    """Write two import roots connected by one direct project call."""

    application: Path = root / "services/acme"
    library: Path = root / "libraries/shared"
    application.mkdir(parents=True)
    library.mkdir(parents=True)
    (application / "entry.py").write_text(
        "from shared.steps import step\n\ndef run() -> None:\n    step()\n",
        encoding="utf-8",
    )
    (library / "steps.py").write_text("def step() -> None:\n    return None\n", encoding="utf-8")
