"""Helpers for CLI tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import BinaryIO

import pytest

from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config


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
        if self._calls == self._failure_at:
            raise OSError("simulated skill replacement failure")
        return self._publish(staged_file=staged_file)


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
        if self._calls == self._race_at:
            target.write_text(self._user_content, encoding="utf-8")
        self._link(source, target, follow_symlinks=follow_symlinks)


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
        if self._calls == self._race_at:
            replacement: Path = self._target_path.with_name("racing-user-skill")
            replacement.write_text(self._user_content, encoding="utf-8")
            _ = replacement.replace(self._target_path)
        self._write(target_file=target_file, content=content)


def configure_no_color(*, monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    """Set or clear the conventional terminal color opt-out."""

    monkeypatch.delenv("NO_COLOR", raising=False)
    if enabled:
        monkeypatch.setenv("NO_COLOR", "1")


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
        source: str = "VALUE = 1\n" if include_fault else "VALUE: int = 1\n"
        (package / "models.py").write_text(source, encoding="utf-8")
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
    (alternate / "models.py").write_text("VALUE: int = 1\n", encoding="utf-8")
    (root / "specs").mkdir()


def write_init_existing_config(*, root: Path, source: str) -> Path:
    """Write one supported existing config source and return its path."""

    if source == "strata.toml":
        path: Path = root / "strata.toml"
        path.write_text('roots = ["src/acme"]\n', encoding="utf-8")
        return path
    path = root / "pyproject.toml"
    existing: str = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(f'{existing}\n[tool.strata]\nroots = ["src/acme"]\n', encoding="utf-8")
    return path


def project_file_snapshot(root: Path) -> tuple[str, ...]:
    """Return all repository-relative files in stable order."""

    return tuple(
        path.relative_to(root).as_posix() for path in sorted(root.rglob("*")) if path.is_file()
    )


def prepare_init_execution_project(*, root: Path, existing_project: bool) -> tuple[str, ...]:
    """Optionally write an existing project and return its initial file snapshot."""

    if existing_project:
        write_init_hatch_project(root=root)
    return project_file_snapshot(root)


def assert_init_execution_files(
    *,
    root: Path,
    before: tuple[str, ...],
    expected_config: str | None,
    expected_created_paths: tuple[str, ...],
) -> None:
    """Assert atomic refusal or exact successful init filesystem state."""

    if expected_config is None:
        assert project_file_snapshot(root) == before
    else:
        assert (root / "strata.toml").read_text(encoding="utf-8") == expected_config
    if expected_created_paths:
        assert project_file_snapshot(root) == expected_created_paths


def configured_roots_or_none(root: Path) -> tuple[str, ...] | None:
    """Return configured roots when init wrote a config."""

    if not (root / "strata.toml").is_file():
        return None
    config: Config = load_config(root)
    return config.roots


def existing_relative_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return expected relative paths that currently exist."""

    return tuple(path for path in paths if (root / path).is_file())


def prepare_init_refusal_project(*, root: Path, source: str) -> tuple[Path, tuple[str, ...]]:
    """Write one refusal fixture and return its repository and initial snapshot."""

    repository: Path = root / "repo" if source == "parent" else root
    repository.mkdir(exist_ok=True)
    write_init_hatch_project(root=repository)
    if source in {"strata.toml", "tool.strata"}:
        _ = write_init_existing_config(root=repository, source=source)
    if source == "parent":
        _ = write_init_existing_config(root=root, source="strata.toml")
    return repository, project_file_snapshot(repository)


def prepare_init_applicability_project(*, root: Path, existing_project: bool) -> tuple[str, ...]:
    """Prepare an existing or empty repository for option-applicability refusal tests."""

    if existing_project:
        write_init_hatch_project(root=root)
    return project_file_snapshot(root)


def prepare_init_transcript_project(*, root: Path, existing_project: bool) -> None:
    """Prepare the representative repository shape for an exact transcript."""

    if existing_project:
        write_init_single_python_file_project(root=root)


def write_broken_strata_symlink(*, root: Path, outside_target: Path) -> None:
    """Write a local config symlink whose outside target does not exist."""

    (root / "strata.toml").symlink_to(outside_target)


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
