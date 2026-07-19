"""Exercise an installed Fensu wheel's Memory surface on release platforms."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    args: argparse.Namespace = _parser().parse_args()
    _assert_architecture(expected=args.architecture)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_project(root)
        _run(root, "memory", "schema", "documents")
        _write_initial_notes(root)
        _prove_commands(root)
        _prove_atomic_publication(root=root, expected_platform=args.platform)
        _prove_archive_and_skills(root)
        if args.platform == "macos":
            _prove_macos_collisions(root)
    return 0


def _prove_commands(root: Path) -> None:
    _run(root, "memory", "sync")
    _run(root, "memory", "rebuild")
    query = _run(root, "memory", "sql", "SELECT count(*) AS documents FROM memory.documents")
    _require("2" in query.stdout, "SQL did not return the initial document count")
    graph = _run(root, "memory", "graph", "Alpha", "--format", "json")
    payload: dict[str, object] = json.loads(graph.stdout)
    _require(len(payload["nodes"]) == 2, "graph did not resolve the linked document")
    _run(root, "memory", "check")


def _prove_atomic_publication(*, root: Path, expected_platform: str) -> None:
    database = root / ".fensu" / "memory" / "memory.sqlite3"
    prior = database.read_bytes()
    reader = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    cursor = reader.execute("SELECT count(*) FROM documents")
    prior_count: int = cursor.fetchone()[0]
    cursor.close()
    _write_note(
        root,
        "20260718T170002_000000Z__NOTE-gamma.md",
        "# Gamma\n",
    )
    result = _run(root, "memory", "sync", expected=None)
    if expected_platform == "windows" and result.returncode != 0:
        _require(database.read_bytes() == prior, "failed Windows replacement changed prior bytes")
        _require(prior_count == 2, "open Windows reader lost its prior generation")
        reader.close()
        _run(root, "memory", "sync")
    else:
        _require(result.returncode == 0, f"atomic sync failed: {result.stderr}")
        cursor = reader.execute("SELECT count(*) FROM documents")
        retained_count: int = cursor.fetchone()[0]
        cursor.close()
        _require(retained_count == prior_count, "open reader did not retain its generation")
        reader.close()
    published = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    cursor = published.execute("SELECT count(*) FROM documents")
    published_count: int = cursor.fetchone()[0]
    cursor.close()
    published.close()
    _require(published_count == 3, "published generation is incomplete")


def _prove_archive_and_skills(root: Path) -> None:
    _run(root, "memory", "rebuild")
    gamma = ".ai/knowledge/repo/notes/20260718T170002_000000Z__NOTE-gamma.md"
    _run(root, "memory", "archive", gamma, "--yes")
    archived = root / ".ai/_archive/knowledge/repo/notes" / Path(gamma).name
    _require(archived.is_file(), "archive command did not move the explicit note")
    _run(root, "skills", "--target", "opencode", "--install-root", "project")
    skill = root / ".opencode" / "skills" / "fensu-release-proof" / "SKILL.md"
    _require(skill.is_file(), "skills command did not install project guidance")


def _prove_macos_collisions(root: Path) -> None:
    probe = root / "CaseProbe"
    probe.write_text("probe", encoding="utf-8")
    _require((root / "caseprobe").exists(), "macOS runner volume is not case-insensitive")
    _write_note(root, "20260718T170003_000000Z__NOTE-case-target.md", "# Case Target One\n")
    _write_note(root, "20260718T170004_000000Z__NOTE-case-target.md", "# Case Target Two\n")
    _write_note(
        root,
        "20260718T170005_000000Z__NOTE-case-link.md",
        "# Case Link\n\n[[case-target]]\n",
    )
    result = _run(root, "memory", "check", expected=1)
    _require("MEM005" in result.stdout, "ambiguous macOS wikilink did not report MEM005")


def _write_project(root: Path) -> None:
    (root / "src/pkg").mkdir(parents=True)
    (root / "src/pkg/__init__.py").write_text("", encoding="utf-8")
    (root / "fensu.toml").write_text(
        'roots = ["src/pkg"]\n[experimental]\nmemory = true\n[skills]\nname = "release-proof"\n',
        encoding="utf-8",
    )


def _write_initial_notes(root: Path) -> None:
    _write_note(
        root,
        "20260718T170000_000000Z__NOTE-alpha.md",
        "# Alpha\n\n[[beta]]\n",
    )
    _write_note(root, "20260718T170001_000000Z__NOTE-beta.md", "# Beta\n")


def _write_note(root: Path, name: str, contents: str) -> None:
    parent = root / ".ai/knowledge/repo/notes"
    parent.mkdir(parents=True, exist_ok=True)
    (parent / name).write_text(contents, encoding="utf-8")


def _run(root: Path, *arguments: str, expected: int | None = 0) -> subprocess.CompletedProcess[str]:
    executable = Path(sys.executable).with_name("fensu.exe" if os.name == "nt" else "fensu")
    environment = dict(os.environ)
    environment["NO_COLOR"] = "1"
    result = subprocess.run(
        (str(executable), *arguments),
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if expected is not None:
        _require(
            result.returncode == expected,
            f"{' '.join(arguments)} returned {result.returncode}: {result.stderr}",
        )
    return result


def _assert_architecture(*, expected: str) -> None:
    actual = platform.machine().lower()
    aliases = {"x86_64": {"x86_64", "amd64"}, "aarch64": {"aarch64", "arm64"}}
    _require(actual in aliases[expected], f"expected {expected} runner, found {actual}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("windows", "macos"), required=True)
    parser.add_argument("--architecture", choices=("x86_64", "aarch64"), required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
