"""Helpers for CLI tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import BinaryIO

import pytest

from strata.agentdocs.constants import GENERATED_MARKER
from strata.agentdocs.exceptions import SkillInstallError
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results._helpers.conversion import restore_file_evaluation
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.models import CachedFileResult, CacheIndexEntry
from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from strata.cli.main.skills import run_skills
from strata.config.main.load_config import load_config
from strata.config.models import Config
from strata.evaluation.models import FileEvaluation


class CaptureOutput(StringIO):
    """Small text sink with configurable terminal-color support."""

    def __init__(self, *, is_terminal: bool = False) -> None:
        super().__init__()
        self._is_terminal: bool = is_terminal

    def isatty(self) -> bool:
        return self._is_terminal


class TerminalBuffer(StringIO):
    """Scripted text terminal with independently configurable TTY support."""

    def __init__(self, content: str = "", *, is_terminal: bool = True) -> None:
        super().__init__(content)
        self._is_terminal: bool = is_terminal

    def isatty(self) -> bool:
        return self._is_terminal


class FailingSkillPublisher:
    """Publish staged skills in order and fail at one configured commit."""

    def __init__(self, *, failure_at: int, publish: Callable[..., object]) -> None:
        self._failure_at: int = failure_at
        self._publish: Callable[..., object] = publish
        self._calls: int = 0

    def __call__(self, *, staged_file: object) -> object:
        self._calls += 1
        publish: Callable[..., object] = {
            False: self._publish_staged_file,
            True: self._raise_failure,
        }[self._calls == self._failure_at]
        return publish(staged_file=staged_file)

    def _publish_staged_file(self, *, staged_file: object) -> object:
        return self._publish(staged_file=staged_file)

    def _raise_failure(self, *, staged_file: object) -> object:
        del staged_file
        raise OSError("simulated skill replacement failure")


class RacingSkillLinker:
    """Create a user file after validation before one staged publication."""

    def __init__(
        self,
        *,
        race_at: int,
        user_content: str,
        link: Callable[..., None],
    ) -> None:
        self._race_at: int = race_at
        self._user_content: str = user_content
        self._link: Callable[..., None] = link
        self._calls: int = 0

    def __call__(self, source: Path, target: Path, *, follow_symlinks: bool) -> None:
        self._calls += 1
        race: Callable[[], None] = {False: lambda: None, True: lambda: self._race(target)}[
            self._calls == self._race_at
        ]
        race()
        self._link(source, target, follow_symlinks=follow_symlinks)

    def _race(self, target: Path) -> None:
        target.write_text(self._user_content, encoding="utf-8")


class RacingExistingSkillWriter:
    """Replace a target pathname after its writable descriptor is verified."""

    def __init__(
        self,
        *,
        race_at: int,
        target_path: Path,
        user_content: str,
        write: Callable[..., None],
    ) -> None:
        self._race_at: int = race_at
        self._target_path: Path = target_path
        self._user_content: str = user_content
        self._write: Callable[..., None] = write
        self._calls: int = 0

    def __call__(self, *, target_file: BinaryIO, content: bytes) -> None:
        self._calls += 1
        race: Callable[[], None] = {False: lambda: None, True: self._race}[
            self._calls == self._race_at
        ]
        race()
        self._write(target_file=target_file, content=content)

    def _race(self) -> None:
        replacement: Path = self._target_path.with_name("racing-user-skill")
        replacement.write_text(self._user_content, encoding="utf-8")
        _ = replacement.replace(self._target_path)


class FailingSkillDeleter:
    """Fail one staged legacy deletion after earlier deletions were published."""

    def __init__(self, *, failure_at: int, delete: Callable[..., object]) -> None:
        self._failure_at: int = failure_at
        self._delete: Callable[..., object] = delete
        self._calls: int = 0

    def __call__(self, *, staged: object) -> object:
        self._calls += 1
        action: Callable[[], object] = {
            False: lambda: self._delete(staged=staged),
            True: self._fail,
        }[self._calls == self._failure_at]
        return action()

    def _fail(self) -> object:
        raise SkillInstallError("simulated legacy deletion failure")


class RacingLegacyRenamer:
    """Replace a captured legacy file immediately before its quarantine rename."""

    def __init__(
        self,
        *,
        legacy_path: Path,
        user_content: str,
        rename: Callable[..., Path],
    ) -> None:
        self._legacy_path: Path = legacy_path
        self._user_content: str = user_content
        self._rename: Callable[..., Path] = rename
        self._raced: bool = False

    def __call__(self, source: Path, target: Path) -> Path:
        should_race: bool = source == self._legacy_path and not self._raced
        action: Callable[[], None] = {
            False: lambda: None,
            True: self._race,
        }[should_race]
        action()
        return self._rename(source, target)

    def _race(self) -> None:
        self._raced = True
        replacement: Path = self._legacy_path.with_name("racing-user-legacy")
        replacement.write_text(self._user_content, encoding="utf-8")
        _ = replacement.replace(self._legacy_path)


def configure_no_color(*, monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    """Set or clear the conventional terminal color opt-out."""

    monkeypatch.delenv("NO_COLOR", raising=False)
    configure: Callable[[], None] = {
        False: lambda: None,
        True: lambda: monkeypatch.setenv("NO_COLOR", "1"),
    }[enabled]
    configure()


def write_init_hatch_project(
    *,
    root: Path,
    package_paths: tuple[str, ...] = ("src/acme",),
    tooling_paths: tuple[str, ...] = (),
    include_fault: bool = True,
) -> None:
    """Write an existing Hatch package with optional Python tooling directories."""

    packages: str = ", ".join(f'"{path}"' for path in package_paths)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "acme"\n[tool.hatch.build.targets.wheel]\npackages = [{packages}]\n',
        encoding="utf-8",
    )
    for package_path in package_paths:
        package: Path = root / package_path
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        source: str = {False: "VALUE: int = 1\n", True: "VALUE = 1\n"}[include_fault]
        (package / "constants.py").write_text(source, encoding="utf-8")
    (root / "tests").mkdir()
    for tooling_path in tooling_paths:
        tooling: Path = root / tooling_path
        tooling.mkdir(parents=True)
        (tooling / "task.py").write_text("def run() -> None:\n    pass\n", encoding="utf-8")


def write_init_single_python_file_project(*, root: Path) -> None:
    """Write a Hatch package whose sole Python file has one gradual-rule fault."""

    package: Path = root / "src/acme"
    package.mkdir(parents=True)
    (root / "tests").mkdir()
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "acme"\n[tool.hatch.build.targets.wheel]\npackages = ["src/acme"]\n',
        encoding="utf-8",
    )


def write_init_invalid_python_project(*, root: Path) -> None:
    """Write a detectable Hatch package whose drift evaluation cannot parse Python."""

    write_init_hatch_project(root=root)
    (root / "src/acme/models.py").write_text("def broken(:\n", encoding="utf-8")


def write_init_invalid_utf8_project(*, root: Path) -> None:
    """Write a detectable Hatch package containing invalid UTF-8 Python bytes."""

    write_init_hatch_project(root=root)
    (root / "src/acme/models.py").write_bytes(b"\xff\xfe\x00")


def write_init_editable_project(*, root: Path) -> None:
    """Write detected and alternate roots and tests for aggregate editing."""

    write_init_hatch_project(root=root)
    alternate: Path = root / "vendor/lib/other"
    alternate.mkdir(parents=True)
    (alternate / "__init__.py").write_text("", encoding="utf-8")
    (alternate / "constants.py").write_text("VALUE: int = 1\n", encoding="utf-8")
    (root / "specs").mkdir()


def write_init_existing_config(*, root: Path, source: str) -> Path:
    """Write one supported existing config source and return its path."""

    def write_strata_config() -> Path:
        path: Path = root / "strata.toml"
        path.write_text('roots = ["src/acme"]\n', encoding="utf-8")
        return path

    def write_pyproject_config() -> Path:
        path: Path = root / "pyproject.toml"
        try:
            existing: str = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            existing = ""
        path.write_text(f'{existing}\n[tool.strata]\nroots = ["src/acme"]\n', encoding="utf-8")
        return path

    writer: Callable[[], Path] = {
        "strata.toml": write_strata_config,
        "tool.strata": write_pyproject_config,
    }[source]
    return writer()


def project_file_snapshot(root: Path) -> tuple[str, ...]:
    """Return all repository-relative files in stable order."""

    paths: filter[Path] = filter(Path.is_file, sorted(root.rglob("*")))
    return tuple(path.relative_to(root).as_posix() for path in paths)


def prepare_init_execution_project(*, root: Path, existing_project: bool) -> tuple[str, ...]:
    """Optionally write an existing project and return its initial file snapshot."""

    prepare: Callable[[], None] = {
        False: lambda: None,
        True: lambda: write_init_hatch_project(root=root),
    }[existing_project]
    prepare()
    return project_file_snapshot(root)


def assert_init_execution_files(
    *,
    root: Path,
    before: tuple[str, ...],
    expected_config: str | None,
    expected_created_paths: tuple[str, ...],
) -> None:
    """Assert atomic refusal or exact successful init filesystem state."""

    def assert_refusal() -> None:
        assert project_file_snapshot(root) == before

    def assert_success() -> None:
        assert expected_config is not None
        assert (root / "strata.toml").read_text(encoding="utf-8") == expected_config

    assertion: Callable[[], None] = {
        True: assert_refusal,
        False: assert_success,
    }[expected_config is None]
    assertion()
    for expected_paths in filter(None, (expected_created_paths,)):
        assert project_file_snapshot(root) == expected_paths


def configured_roots_or_none(root: Path) -> tuple[str, ...] | None:
    """Return configured roots when init wrote a config."""

    try:
        _ = (root / "strata.toml").stat()
    except FileNotFoundError:
        return None
    config: Config = load_config(root)
    return config.roots


def existing_relative_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return expected relative paths that currently exist."""

    return tuple(filter(lambda path: (root / path).is_file(), paths))


def prepare_init_refusal_project(*, root: Path, source: str) -> tuple[Path, tuple[str, ...]]:
    """Write one refusal fixture and return its repository and initial snapshot."""

    repository: Path = {False: root, True: root / "repo"}[source == "parent"]
    repository.mkdir(exist_ok=True)
    write_init_hatch_project(root=repository)
    write_local: Callable[[], object] = {
        False: lambda: None,
        True: lambda: write_init_existing_config(root=repository, source=source),
    }[source in {"strata.toml", "tool.strata"}]
    write_parent: Callable[[], object] = {
        False: lambda: None,
        True: lambda: write_init_existing_config(root=root, source="strata.toml"),
    }[source == "parent"]
    _ = write_local()
    _ = write_parent()
    return repository, project_file_snapshot(repository)


def prepare_init_applicability_project(*, root: Path, existing_project: bool) -> tuple[str, ...]:
    """Prepare an existing or empty repository for option-applicability refusal tests."""

    prepare: Callable[[], None] = {
        False: lambda: None,
        True: lambda: write_init_hatch_project(root=root),
    }[existing_project]
    prepare()
    return project_file_snapshot(root)


def prepare_init_transcript_project(*, root: Path, existing_project: bool) -> None:
    """Prepare the representative repository shape for an exact transcript."""

    prepare: Callable[[], None] = {
        False: lambda: None,
        True: lambda: write_init_single_python_file_project(root=root),
    }[existing_project]
    prepare()


def write_broken_strata_symlink(*, root: Path, outside_target: Path) -> None:
    """Write a local config symlink whose outside target does not exist."""

    (root / "strata.toml").symlink_to(outside_target)


def prepare_unsafe_local_config_target(*, root: Path, target_kind: str) -> Path:
    """Create a symlink or nonregular local configuration candidate."""

    name: str = {False: "strata.toml", True: "pyproject.toml"}[target_kind.startswith("pyproject")]
    path: Path = root / name

    def create_symlink() -> None:
        outside: Path = root.parent / f"{root.name}-{name}"
        outside.write_text('[tool.strata]\nroots = ["src/pkg"]\n', encoding="utf-8")
        path.symlink_to(outside)

    def create_directory() -> None:
        path.mkdir()

    create: Callable[[], None] = {
        False: create_directory,
        True: create_symlink,
    }[target_kind.endswith("symlink")]
    create()
    return path


def write_selected_root_python_symlink(*, root: Path, outside_target: Path) -> None:
    """Write an outside Python file and a selected-root symlink pointing to it."""

    outside_target.write_text("OUTSIDE_VALUE: int = 1\n", encoding="utf-8")
    (root / "src/acme/external.py").symlink_to(outside_target)


def write_cli_fixture_project(
    *, root: Path, rule_code: str, include_core_rules: bool = False
) -> None:
    """Write a tiny project with one custom rule that always reports a fault."""

    (root / "src" / "pkg").mkdir(parents=True)
    (root / "rules").mkdir()
    (root / "src" / "pkg" / "target.py").write_text("value: int = 1\n", encoding="utf-8")
    selected_rules: str = {
        False: f'"{rule_code}"',
        True: f'"SF", "{rule_code}"',
    }[include_core_rules]
    ignored_rules: str = {False: "", True: 'ignore = ["SFH002"]\n'}[include_core_rules]
    config: str = (
        f'roots = ["src/pkg"]\nselect = [{selected_rules}]\n{ignored_rules}'
        'rule_paths = ["rules/custom_rule.py"]\n'
        '[skills]\nname = "fixture"\n'
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


def write_cli_warning_skill_project(*, root: Path, rule_code: str) -> None:
    """Write a project with separate blocking and custom warning selections."""

    write_cli_fixture_project(root=root, rule_code=rule_code)
    (root / "strata.toml").write_text(
        'roots = ["src/pkg"]\n'
        'select = ["SFN001"]\n'
        f'warn = ["{rule_code}"]\n'
        'ignore = ["SFH002"]\n'
        'rule_paths = ["rules/custom_rule.py"]\n'
        '[skills]\nname = "fixture"\n',
        encoding="utf-8",
    )


def write_custom_rule_coverage_project(
    *,
    root: Path,
    test_source: str | None,
    minimum: int,
    use_rule_module: bool,
    second_rule: bool,
    warn_only: bool = False,
) -> None:
    """Write a repository-owned custom-rule coverage fixture."""

    (root / "src/pkg").mkdir(parents=True)
    (root / "src/pkg/target.py").write_text("VALUE: int = 1\n", encoding="utf-8")
    (root / "rules").mkdir()
    (root / "rules/__init__.py").write_text("", encoding="utf-8")
    registration_key: str = {False: "rule_paths", True: "rule_modules"}[use_rule_module]
    registration_value: str = {
        False: '"rules/custom_rule.py"',
        True: '"rules.custom_rule"',
    }[use_rule_module]
    selection: str = {
        False: 'select = ["SFR707"]\n',
        True: 'select = ["SFA101"]\nwarn = ["SFR707"]\n',
    }[warn_only]
    (root / "strata.toml").write_text(
        f'roots = ["src/pkg"]\ntests = ["tests"]\n{selection}'
        f"{registration_key} = [{registration_value}]\n"
        f"[thresholds]\nmin_custom_rule_test_cases = {minimum}\n",
        encoding="utf-8",
    )
    second_source: str = {
        False: "",
        True: (
            "\n@rule(code='XCV002', family=Family.CUSTOM, slug='second', message='second')\n"
            "def second_rule(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
            "    del module, ctx\n"
            "    return []\n"
        ),
    }[second_rule]
    (root / "rules/custom_rule.py").write_text(
        "from __future__ import annotations\n\n"
        "import ast\n\n"
        "from strata import Family, Fault, RuleContext, rule\n\n"
        "@rule(code='XCV001', family=Family.CUSTOM, slug='first', message='first')\n"
        "def first_rule(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    del module, ctx\n"
        "    return []\n"
        f"{second_source}",
        encoding="utf-8",
    )
    write_test: Callable[[], object] = {
        False: lambda: None,
        True: lambda: _write_custom_rule_test(root=root, source=test_source or ""),
    }[test_source is not None]
    _ = write_test()


def _write_custom_rule_test(*, root: Path, source: str) -> None:
    tests: Path = root / "tests"
    tests.mkdir()
    (tests / "test_custom_rule.py").write_text(source, encoding="utf-8")


def generated_skill_text(*, root: Path, body: str) -> str:
    """Build same-owner generated content for installation transaction tests."""

    owner: str = hashlib.sha256(
        (root / "strata.toml").resolve().as_posix().encode("utf-8")
    ).hexdigest()
    marker: str = json.dumps(
        {
            "content_fingerprint": "content",
            "identity": "strata-fixture",
            "input_fingerprint": "input",
            "owner": owner,
            "schema": 1,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    generated: str = "<!-- generated-by: strata skills update -->"
    return f"{generated}\n<!-- strata-skill-owner: {marker} -->\n{body}"


def complete_filesystem_snapshot(root: Path) -> tuple[tuple[str, str, int, int, bytes], ...]:
    """Return paths, kinds, modes, mtimes, and bytes for a complete logical tree snapshot."""

    entries: list[tuple[str, str, int, int, bytes]] = []
    for path in sorted(root.rglob("*")):
        metadata: os.stat_result = path.lstat()
        path_state: tuple[bool, bool] = (path.is_symlink(), path.is_dir())
        kind: str = {
            (False, False): "file",
            (False, True): "directory",
            (True, False): "symlink",
            (True, True): "symlink",
        }[path_state]
        content: bytes = {
            False: lambda: b"",
            True: path.read_bytes,
        }[path.is_file() and not path.is_symlink()]()
        entries.append(
            (
                path.relative_to(root).as_posix(),
                kind,
                metadata.st_mode,
                metadata.st_mtime_ns,
                content,
            )
        )
    return tuple(entries)


def mutate_skill_freshness_state(*, root: Path, state: str) -> None:
    """Apply one named post-install freshness state without test-body branching."""

    path: Path = root / ".agents/skills/strata-fixture/SKILL.md"
    mutations: dict[str, Callable[[], object]] = {
        "current": lambda: None,
        "missing": path.unlink,
        "stale": lambda: (root / "strata.toml").write_text(
            (root / "strata.toml").read_text(encoding="utf-8") + "\n[cache]\nenabled = false\n",
            encoding="utf-8",
        ),
        "divergent": lambda: path.write_bytes(path.read_bytes() + b"manual change\n"),
        "malformed-marker": lambda: path.write_text(
            re.sub(
                r"<!-- strata-skill-owner: .* -->",
                "<!-- strata-skill-owner: malformed -->",
                path.read_text(encoding="utf-8"),
                count=1,
            ),
            encoding="utf-8",
        ),
        "collision": lambda: path.write_text("user-authored skill\n", encoding="utf-8"),
    }
    _ = mutations[state]()


def prepare_normal_check_skill_state(*, root: Path, state: str) -> None:
    """Install or create one local skill state used by normal-check freshness tests."""

    path: Path = root / ".agents/skills/strata-fixture/SKILL.md"
    preparations: dict[str, Callable[[], object]] = {
        "declined": lambda: None,
        "unmanaged": lambda: _write_user_skill(path),
        "malformed-marker": lambda: _write_malformed_skill(path),
        "current": lambda: run_skills(argv=("--target", "agents")),
        "divergent": lambda: _install_then_mutate(root=root, state="divergent"),
        "stale-all": lambda: _install_all_then_stale(root),
    }
    _ = preparations[state]()


def fail_skill_renderer(**kwargs: object) -> str:
    """Fail if the normal-check freshness path invokes Markdown generation."""

    del kwargs
    raise AssertionError("normal check invoked the full skill renderer")


class SkillReadCounter:
    """Count bounded target probes while preserving the real reader."""

    def __init__(self, read: Callable[[Path], tuple[bytes | None, bool]]) -> None:
        """Store the real target reader and initialize the operation count."""

        self.calls: int = 0
        self._read: Callable[[Path], tuple[bytes | None, bool]] = read

    def __call__(self, path: Path) -> tuple[bytes | None, bool]:
        """Record and delegate one target probe."""

        self.calls += 1
        return self._read(path)


def _write_user_skill(path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text("user-authored skill\n", encoding="utf-8")


def _write_malformed_skill(path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        f"{GENERATED_MARKER}\n<!-- strata-skill-owner: malformed -->\n",
        encoding="utf-8",
    )


def _install_then_mutate(*, root: Path, state: str) -> None:
    _ = run_skills(argv=("--target", "agents"))
    mutate_skill_freshness_state(root=root, state=state)


def _install_all_then_stale(root: Path) -> None:
    _ = run_skills(argv=())
    config: Path = root / "strata.toml"
    config.write_text(
        config.read_text(encoding="utf-8") + "\n[cache]\nenabled = false\n",
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
        "[thresholds]\n"
        "max_positional_args = 0\n"
        "[[rule_exceptions]]\n"
        'rule = "SFS120"\n'
        'path = "src/pkg/external.py"\n'
        'symbols = ["callback"]\n'
        'reason = "The external API invokes this callback positionally."\n',
        encoding="utf-8",
    )


def write_cli_file_exception_project(root: Path) -> None:
    """Write a project whose only path-level core fault is exactly excepted."""

    source: Path = root / "src/pkg/domain/special.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    (root / "strata.toml").write_text(
        'roots = ["src/pkg"]\n'
        'select = ["SFR307"]\n'
        "[[rule_exceptions]]\n"
        'rule = "SFR307"\n'
        'path = "src/pkg/domain/special.py"\n'
        'reason = "This module is an intentional compatibility adapter."\n',
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
    cache_config: str = {
        None: "",
        False: "[cache]\nenabled = false\n",
        True: "[cache]\nenabled = true\n",
    }[cache_enabled]
    (root / "strata.toml").write_text(
        f'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n{cache_config}',
        encoding="utf-8",
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
    write_configuration: Callable[[], object] = {
        False: lambda: None,
        True: lambda: (root / "strata.toml").write_text(
            f'roots = ["{configured_root}"]\n', encoding="utf-8"
        ),
    }[write_config]
    _ = write_configuration()
    parameters: str = {False: "", True: "callback: object"}[dynamic_seam]
    callback_line: str = {False: "", True: "    callback()"}[dynamic_seam]
    step_import: str = {
        False: f"from {package_name}.steps import step",
        True: "from .steps import step",
    }[relative_imports]
    function_lines: tuple[str, ...] = {
        False: ("    step()", callback_line),
        True: (callback_line, "    step()"),
    }[dynamic_first]
    function_body: str = "\n".join(filter(None, function_lines))
    (package / "entry.py").write_text(
        (f"{step_import}\n\ndef run({parameters}) -> None:\n{function_body}\n"),
        encoding="utf-8",
    )
    finish_import: str = {
        False: f"import {package_name}.finish as finishing",
        True: "from . import finish as finishing",
    }[relative_imports]
    (package / "steps.py").write_text(
        f"{finish_import}\n\ndef step() -> None:\n    finishing.finish()\n",
        encoding="utf-8",
    )
    finish_source: str = {
        False: "def finish() -> None:\n    return None\n",
        True: f"from {package_name}.entry import run\n\ndef finish() -> None:\n    run()\n",
    }[cycle]
    (package / "finish.py").write_text(finish_source, encoding="utf-8")
    write_ambiguous: Callable[[], object] = {
        False: lambda: None,
        True: lambda: (package / "other.py").write_text(
            "def run() -> None:\n    return None\n", encoding="utf-8"
        ),
    }[ambiguous]
    _ = write_ambiguous()


def write_cli_method_map_project(root: Path) -> None:
    """Write a configured project exercising conservative method resolution."""

    package: Path = root / "src/methods"
    package.mkdir(parents=True)
    (root / "strata.toml").write_text('roots = ["src/methods"]\n', encoding="utf-8")
    (package / "support.py").write_text(
        "class Helper:\n    def finish(self) -> None:\n        return None\n",
        encoding="utf-8",
    )
    (package / "imported.py").write_text(
        "class ImportedWorker:\n    def imported_method(self) -> None:\n        return None\n",
        encoding="utf-8",
    )
    (package / "workers.py").write_text(
        "from methods.support import Helper\n"
        "\n"
        "\n"
        "class Worker:\n"
        "    def __init__(self) -> None:\n"
        "        self.helper: Helper = Helper()\n"
        "\n"
        "    def execute(self) -> None:\n"
        "        self.prepare()\n"
        "\n"
        "    def prepare(self) -> None:\n"
        "        self.helper.finish()\n"
        "\n"
        "    @classmethod\n"
        "    def create(cls) -> Worker:\n"
        "        cls.class_step()\n"
        "        return cls()\n"
        "\n"
        "    @classmethod\n"
        "    def class_step(cls) -> None:\n"
        "        return None\n"
        "\n"
        "    def cycle_one(self) -> None:\n"
        "        self.cycle_two()\n"
        "\n"
        "    def cycle_two(self) -> None:\n"
        "        self.cycle_one()\n"
        "\n"
        "\n"
        "class Alpha:\n"
        "    def select(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class Beta:\n"
        "    def select(self) -> None:\n"
        "        return None\n",
        encoding="utf-8",
    )
    (package / "alternate.py").write_text(
        "class Alpha:\n    def select(self) -> None:\n        return None\n",
        encoding="utf-8",
    )
    (package / "entry.py").write_text(
        "from pathlib import Path\n"
        "from typing import Protocol\n"
        "\n"
        "import methods.imported as imported\n"
        "from methods.workers import Worker\n"
        "\n"
        "\n"
        "class RunnerProtocol(Protocol):\n"
        "    def execute(self) -> None:\n"
        "        ...\n"
        "\n"
        "\n"
        "class LocalWorker:\n"
        "    def local_method(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "def make_worker() -> Worker:\n"
        "    return Worker()\n"
        "\n"
        "\n"
        "def run(protocol: RunnerProtocol, dynamic, path: Path) -> None:\n"
        "    worker = Worker()\n"
        "    worker.execute()\n"
        "    Worker().prepare()\n"
        "    make_worker().execute()\n"
        "    Worker.create()\n"
        "    imported.ImportedWorker().imported_method()\n"
        "    local = LocalWorker()\n"
        "    local.local_method()\n"
        "    protocol.execute()\n"
        "    dynamic.parameter_method()\n"
        "    path.exists()\n"
        "\n"
        "\n"
        "def infer_order() -> None:\n"
        "    late.prepare()\n"
        "    late = Worker()\n"
        "    stable = Worker()\n"
        "    stable.execute()\n"
        "    stable = object()\n"
        "    stable.prepare()\n"
        "    invalid = object()\n"
        "    invalid.execute()\n"
        "\n"
        "\n"
        "def direct_dispatch() -> None:\n"
        "    Worker().prepare()\n"
        "\n"
        "\n"
        "def factory_dispatch() -> None:\n"
        "    make_worker().execute()\n",
        encoding="utf-8",
    )
    (package / "generic_protocol.py").write_text(
        "from typing import Protocol, TypeVar\n"
        "\n"
        'T = TypeVar("T")\n'
        "\n"
        "\n"
        "class GenericRunner(Protocol[T]):\n"
        "    def execute(self) -> T:\n"
        "        ...\n"
        "\n"
        "\n"
        "def run_generic(runner: GenericRunner[int]) -> None:\n"
        "    runner.execute()\n",
        encoding="utf-8",
    )
    (package / "nominal_protocols.py").write_text(
        "from typing import Protocol\n"
        "\n"
        "\n"
        "class UniqueProtocol(Protocol):\n"
        "    def execute(self) -> None:\n"
        "        ...\n"
        "\n"
        "\n"
        "class SharedProtocol(Protocol):\n"
        "    def execute(self) -> None:\n"
        "        ...\n"
        "\n"
        "\n"
        "class MissingProtocol(Protocol):\n"
        "    def execute(self) -> None:\n"
        "        ...\n"
        "\n"
        "\n"
        "class IncompleteProtocol(Protocol):\n"
        "    def execute(self) -> None:\n"
        "        ...\n"
        "\n"
        "\n"
        "class InheritedProtocol(Protocol):\n"
        "    def execute(self) -> None:\n"
        "        ...\n",
        encoding="utf-8",
    )
    (package / "nominal.py").write_text(
        "import methods.nominal_protocols as contracts\n"
        "from methods.nominal_protocols import (\n"
        "    IncompleteProtocol,\n"
        "    MissingProtocol,\n"
        "    SharedProtocol,\n"
        "    UniqueProtocol as UniqueContract,\n"
        ")\n"
        "\n"
        "\n"
        "class UniqueRunner(UniqueContract):\n"
        "    def execute(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class FirstRunner(SharedProtocol):\n"
        "    def execute(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class SecondRunner(SharedProtocol):\n"
        "    def execute(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class IncompleteRunner(IncompleteProtocol):\n"
        "    pass\n"
        "\n"
        "\n"
        "class RunnerBase:\n"
        "    def execute(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class InheritedRunner(RunnerBase, contracts.InheritedProtocol):\n"
        "    pass\n"
        "\n"
        "\n"
        "class UnrelatedRunner:\n"
        "    def execute(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "def run_unique(runner: UniqueContract) -> None:\n"
        "    runner.execute()\n"
        "\n"
        "\n"
        "def run_shared(runner: SharedProtocol) -> None:\n"
        "    runner.execute()\n"
        "\n"
        "\n"
        "def run_missing(runner: MissingProtocol) -> None:\n"
        "    runner.execute()\n"
        "\n"
        "\n"
        "def run_incomplete(runner: IncompleteProtocol) -> None:\n"
        "    runner.execute()\n"
        "\n"
        "\n"
        "def run_inherited(runner: contracts.InheritedProtocol) -> None:\n"
        "    runner.execute()\n",
        encoding="utf-8",
    )
    (package / "inference_cases.py").write_text(
        "from methods.entry import make_worker\n"
        "from methods.workers import Worker\n"
        "\n"
        "\n"
        "def conditional_rebind(flag: bool) -> None:\n"
        "    worker = Worker()\n"
        "    if flag:\n"
        "        worker = object()\n"
        "    worker.prepare()\n"
        "\n"
        "\n"
        "def assigned_factory() -> None:\n"
        "    worker = make_worker()\n"
        "    worker.execute()\n",
        encoding="utf-8",
    )
    (package / "inheritance.py").write_text(
        "class Base:\n"
        "    def run(self) -> None:\n"
        "        self.hook()\n"
        "\n"
        "    def hook(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class Child(Base):\n"
        "    def hook(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class Sibling(Base):\n"
        "    def hook(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "def run_children() -> None:\n"
        "    Child().run()\n"
        "    Sibling().run()\n"
        "\n"
        "\n"
        "class Left:\n"
        "    def collide(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class Right:\n"
        "    def collide(self) -> None:\n"
        "        return None\n"
        "\n"
        "\n"
        "class Ambiguous(Left, Right):\n"
        "    pass\n"
        "\n"
        "\n"
        "def run_ambiguous() -> None:\n"
        "    Ambiguous().collide()\n",
        encoding="utf-8",
    )
    (package / "type_order.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from methods.workers import Alpha as Selected\n"
        "\n"
        "from methods.imported import ImportedWorker as Selected\n"
        "\n"
        "\n"
        "def run_selected() -> None:\n"
        "    Selected().imported_method()\n",
        encoding="utf-8",
    )
    (package / "parameter_collision.py").write_text(
        "from methods.workers import Worker\n"
        "\n"
        "\n"
        "def run_collision(Worker) -> None:\n"
        "    Worker.execute()\n",
        encoding="utf-8",
    )
    (package / "shadow_target.py").write_text(
        "def imported_call() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (package / "alias_shadow.py").write_text(
        "import methods.shadow_target as target\n"
        "\n"
        "\n"
        "def run_shadowed() -> None:\n"
        "    target = object()\n"
        "    target.imported_call()\n",
        encoding="utf-8",
    )
    (package / "self_attribute_flow.py").write_text(
        "from methods.support import Helper\n"
        "\n"
        "\n"
        "class Owner:\n"
        "    def __init__(self) -> None:\n"
        "        self.helper = Helper()\n"
        "\n"
        "    def invalidate(self, flag: bool) -> None:\n"
        "        if flag:\n"
        "            self.helper = object()\n"
        "\n"
        "    def use(self) -> None:\n"
        "        self.helper.finish()\n"
        "\n"
        "\n"
        "def run_owner() -> None:\n"
        "    Owner().use()\n",
        encoding="utf-8",
    )
    (package / "type_else.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from methods.workers import Alpha as Selected\n"
        "else:\n"
        "    from methods.imported import ImportedWorker as Selected\n"
        "\n"
        "\n"
        "def run_else_selected() -> None:\n"
        "    Selected().imported_method()\n",
        encoding="utf-8",
    )
    (package / "constructor_assignment_shadow.py").write_text(
        "from methods.workers import Worker\n"
        "\n"
        "\n"
        "def run_constructor_shadow(Worker) -> None:\n"
        "    receiver = Worker()\n"
        "    receiver.execute()\n",
        encoding="utf-8",
    )
    (package / "factory_target.py").write_text(
        "from methods.workers import Worker\n"
        "\n"
        "\n"
        "def make_worker() -> Worker:\n"
        "    return Worker()\n",
        encoding="utf-8",
    )
    (package / "factory_alias_shadow.py").write_text(
        "import methods.factory_target as factories\n"
        "\n"
        "\n"
        "def run_factory_shadow() -> None:\n"
        "    factories = object()\n"
        "    worker = factories.make_worker()\n"
        "    worker.execute()\n",
        encoding="utf-8",
    )
    (package / "type_mixed.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from methods.entry import RunnerProtocol as Selected\n"
        "else:\n"
        "    from methods.workers import Worker as Selected\n"
        "\n"
        "\n"
        "def run_mixed(receiver: Selected) -> None:\n"
        "    receiver.execute()\n"
        "    Selected().execute()\n",
        encoding="utf-8",
    )
    (package / "class_attribute_flow.py").write_text(
        "from methods.support import Helper\n"
        "\n"
        "\n"
        "class DirectOwner:\n"
        "    helper: Helper\n"
        "    helper = object()\n"
        "\n"
        "    def use(self) -> None:\n"
        "        self.helper.finish()\n"
        "\n"
        "\n"
        "class ConditionalOwner:\n"
        "    helper: Helper\n"
        "    if True:\n"
        "        helper = object()\n"
        "\n"
        "    def use(self) -> None:\n"
        "        self.helper.finish()\n"
        "\n"
        "\n"
        "def run_attributes() -> None:\n"
        "    DirectOwner().use()\n"
        "    ConditionalOwner().use()\n",
        encoding="utf-8",
    )


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


class RestoreProbe:
    """Count and delegate warm-path record restores."""

    def __init__(self) -> None:
        """Start with no observed restores."""

        self.calls: int = 0

    def __call__(self, *, result: CachedFileResult, repo_root: Path) -> FileEvaluation:
        """Record one restore and delegate to the real conversion."""

        self.calls += 1
        return restore_file_evaluation(result=result, repo_root=repo_root)


class CallCounter:
    """Count observed delegated calls."""

    def __init__(self) -> None:
        """Start with no observed calls."""

        self.calls: int = 0


def counting_load_results(
    counter: CallCounter,
) -> Callable[..., dict[str, CachedFileResult | None]]:
    """Return a load_results replacement that counts and delegates."""

    original: Callable[..., dict[str, CachedFileResult | None]] = ResultCache.load_results

    def _load_results(
        cache: ResultCache,
        *,
        global_fingerprint: CacheFingerprint,
        entries: tuple[CacheIndexEntry, ...],
    ) -> dict[str, CachedFileResult | None]:
        counter.calls += 1
        return original(cache, global_fingerprint=global_fingerprint, entries=entries)

    return _load_results
