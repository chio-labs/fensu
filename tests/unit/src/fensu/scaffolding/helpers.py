"""Local filesystem helpers for scaffolding tests."""

from __future__ import annotations

import os
from collections.abc import Callable
from io import StringIO
from pathlib import Path

from fensu.reporting.classes.cli_style import CliStyle
from fensu.scaffolding._helpers.output import (
    prompt_accept_layout,
    prompt_project_name,
    prompt_root_selection,
    prompt_yes_no,
)
from fensu.scaffolding.models import (
    DetectedRepositoryLayout,
    GitIgnorePlan,
    InitOptions,
    PathCandidate,
    PythonState,
)
from fensu.scaffolding.types import CandidateProvenance
from tests.unit.src.fensu.scaffolding._test_types import (
    DetectionTestCase,
    ExecutionFailureTestCase,
    InteractionDecisionTestCase,
    OptionApplicabilityTestCase,
    ScaffoldSymlinkTestCase,
    ScopeSymlinkTestCase,
)


class RacingGitIgnorePublisher:
    """Replace a captured gitignore with concurrent user content before publication."""

    def __init__(self, *, path: Path, user_content: bytes, publish: Callable[..., None]) -> None:
        self._path: Path = path
        self._user_content: bytes = user_content
        self._publish: Callable[..., None] = publish

    def __call__(self, *, repository: Path, plan: GitIgnorePlan) -> None:
        replacement: Path = self._path.with_name("racing-user-gitignore")
        replacement.write_bytes(self._user_content)
        _ = replacement.replace(self._path)
        self._publish(repository=repository, plan=plan)


class RacingExclusiveOpener:
    """Create a racing destination immediately before an exclusive open."""

    def __init__(
        self,
        *,
        root: Path,
        destination_name: str,
        user_content: bytes,
        open_file: Callable[..., int],
        destination_kind: str = "regular",
        writes: tuple[tuple[Path, bytes], ...] = (),
        replacements: tuple[tuple[Path, bytes], ...] = (),
    ) -> None:
        self._root: Path = root
        self._destination_name: str = destination_name
        self._user_content: bytes = user_content
        self._open_file: Callable[..., int] = open_file
        self._destination_kind: str = destination_kind
        self._writes: tuple[tuple[Path, bytes], ...] = writes
        self._replacements: tuple[tuple[Path, bytes], ...] = replacements
        self._raced: bool = False

    def __call__(
        self,
        path: str | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        should_race: bool = (
            not self._raced
            and Path(path).name == self._destination_name
            and bool(flags & os.O_EXCL)
        )
        race: Callable[[], None] = {
            False: self._skip_race,
            True: self._publish_racing_destination,
        }[should_race]
        race()
        return self._open_file(path, flags, mode, dir_fd=dir_fd)

    def _skip_race(self) -> None:
        return None

    def _publish_racing_destination(self) -> None:
        for path, content in self._writes:
            path.write_bytes(content)
        for path, content in self._replacements:
            replacement: Path = path.with_name(f"racing-user-{path.name}")
            replacement.write_bytes(content)
            _ = replacement.replace(path)
        destination: Path = self._root / self._destination_name
        publish: Callable[[Path], None] = {
            "regular": self._write_regular_destination,
            "symlink": self._write_symlink_destination,
        }[self._destination_kind]
        publish(destination)
        self._raced = True

    def _write_regular_destination(self, destination: Path) -> None:
        destination.write_bytes(self._user_content)

    def _write_symlink_destination(self, destination: Path) -> None:
        destination.symlink_to(self._user_content.decode())


class RacingExclusiveLinker:
    """Create a racing destination immediately before an exclusive hard link."""

    def __init__(
        self,
        *,
        root: Path,
        destination_name: str,
        user_content: bytes,
        link: Callable[..., None],
        destination_kind: str = "regular",
    ) -> None:
        self._root: Path = root
        self._destination_name: str = destination_name
        self._user_content: bytes = user_content
        self._destination_kind: str = destination_kind
        self._link: Callable[..., None] = link
        self._raced: bool = False

    def __call__(self, source: Path, target: Path, *, follow_symlinks: bool) -> None:
        should_race: bool = not self._raced and Path(target).name == self._destination_name
        race: Callable[[], None] = {
            False: self._skip_race,
            True: self._publish_racing_destination,
        }[should_race]
        race()
        self._link(source, target, follow_symlinks=follow_symlinks)

    def _skip_race(self) -> None:
        return None

    def _publish_racing_destination(self) -> None:
        destination: Path = self._root / self._destination_name
        publish: Callable[[Path], None] = {
            "regular": self._write_regular_destination,
            "symlink": self._write_symlink_destination,
        }[self._destination_kind]
        publish(destination)
        self._raced = True

    def _write_regular_destination(self, destination: Path) -> None:
        destination.write_bytes(self._user_content)

    def _write_symlink_destination(self, destination: Path) -> None:
        destination.symlink_to(self._user_content.decode())


class RacingConfigStageLinker:
    """Replace a staged config pathname immediately before publication."""

    def __init__(self, *, user_content: bytes, link: Callable[..., None]) -> None:
        self._user_content: bytes = user_content
        self._link: Callable[..., None] = link

    def __call__(self, source: Path, target: Path, *, follow_symlinks: bool) -> None:
        replacement: Path = source.with_name(f"racing-user-{source.name}")
        replacement.write_bytes(self._user_content)
        _ = replacement.replace(source)
        self._link(source, target, follow_symlinks=follow_symlinks)


class SwappingDirectoryOpener:
    """Swap one scaffold parent for an outside symlink before descriptor opening."""

    def __init__(self, *, root: Path, outside: Path, open_file: Callable[..., int]) -> None:
        self._root: Path = root
        self._outside: Path = outside
        self._open_file: Callable[..., int] = open_file
        self._swapped: bool = False

    def __call__(
        self,
        path: str | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        should_swap: bool = not self._swapped and path == "src" and dir_fd is not None
        swap: Callable[[], None] = {
            False: self._skip_swap,
            True: self._swap_directory,
        }[should_swap]
        swap()
        return self._open_file(path, flags, mode, dir_fd=dir_fd)

    def _skip_swap(self) -> None:
        return None

    def _swap_directory(self) -> None:
        (self._root / "src").rename(self._root / "displaced-src")
        (self._root / "src").symlink_to(self._outside, target_is_directory=True)
        self._swapped = True


class FailingPublicationWriter:
    """Fail a direct descriptor publication after writing a partial prefix."""

    def __init__(self, *, write: Callable[..., int]) -> None:
        self._write: Callable[..., int] = write

    def __call__(self, *, descriptor: int, content: bytes) -> None:
        _ = self._write(descriptor, content[:1])
        raise OSError("direct publication write failed")


class NoDirFdOpener:
    """Model a platform whose open operation rejects dir_fd."""

    def __init__(self, *, open_file: Callable[..., int]) -> None:
        self._open_file: Callable[..., int] = open_file

    def __call__(
        self,
        path: str | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        operation: Callable[..., int] = {
            False: self._open,
            True: self._raise_unavailable,
        }[dir_fd is not None]
        return operation(path=path, flags=flags, mode=mode)

    def _open(self, *, path: str | Path, flags: int, mode: int) -> int:
        return self._open_file(path, flags, mode)

    def _raise_unavailable(self, *, path: str | Path, flags: int, mode: int) -> int:
        del path, flags, mode
        raise NotImplementedError("dir_fd is unavailable")


class CountingFileOpener:
    """Count descriptor opens while delegating to the real OS operation."""

    def __init__(self, *, open_file: Callable[..., int]) -> None:
        self._open_file: Callable[..., int] = open_file
        self.calls: int = 0

    def __call__(self, path: Path, flags: int) -> int:
        self.calls += 1
        return self._open_file(path, flags)


class RacingDescriptorReader:
    """Replace a pathname while its already-open descriptor is being read."""

    def __init__(self, *, path: Path, replacement: bytes, read: Callable[..., bytes]) -> None:
        self._path: Path = path
        self._replacement: bytes = replacement
        self._read: Callable[..., bytes] = read
        self._raced: bool = False

    def __call__(self, descriptor: int, count: int) -> bytes:
        race: Callable[[], None] = {
            False: self._replace_path,
            True: self._skip_race,
        }[self._raced]
        race()
        return self._read(descriptor, count)

    def _replace_path(self) -> None:
        replacement: Path = self._path.with_name("racing-user-pyproject.toml")
        replacement.write_bytes(self._replacement)
        _ = replacement.replace(self._path)
        self._raced = True

    def _skip_race(self) -> None:
        return None


def build_repository(
    *, root: Path, files: tuple[tuple[str, str], ...], directories: tuple[str, ...] = ()
) -> None:
    """Create one tiny repository from relative paths and text."""

    for relative in directories:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative, text in files:
        path: Path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def prepare_root_gitignore(*, root: Path, initial: bytes | None) -> Path:
    """Optionally write initial root gitignore bytes and return its path."""

    path: Path = root / ".gitignore"
    for content in filter(None, (initial,)):
        path.write_bytes(content)
    return path


def gitignore_plan_desired(*, plan: GitIgnorePlan | None) -> bytes | None:
    """Return planned bytes without branching in behavior tests."""

    return getattr(plan, "desired", None)


def gitignore_bytes_or_none(*, path: Path) -> bytes | None:
    """Return root gitignore bytes when the path exists."""

    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def prepare_unsafe_gitignore(*, root: Path, target_kind: str) -> Path:
    """Create one unsafe root gitignore target for refusal coverage."""

    path: Path = root / ".gitignore"
    create: Callable[[], object] = {
        "directory": lambda: path.mkdir(),
        "symlink": lambda: path.symlink_to(root / "outside"),
    }[target_kind]
    create()
    return path


def build_detection_repository(*, root: Path, test_case: DetectionTestCase) -> None:
    """Create the repository declared by a detection test case."""

    build_repository(root=root, files=test_case.files, directories=test_case.directories)


def candidate_details(*, candidates: tuple[PathCandidate, ...]) -> tuple[tuple[str, str], ...]:
    """Return stable root candidate details for assertions."""

    return tuple((candidate.path, candidate.provenance.value) for candidate in candidates)


def candidate_test_details(
    *, candidates: tuple[PathCandidate, ...]
) -> tuple[tuple[str, str, bool], ...]:
    """Return stable test candidate details for assertions."""

    return tuple(
        (candidate.path, candidate.provenance.value, candidate.present) for candidate in candidates
    )


def detected_layout(*, is_empty: bool, has_tooling: bool) -> DetectedRepositoryLayout:
    """Build the smallest detected layout needed by planning tests."""

    tooling: tuple[PathCandidate, ...] = {
        False: (),
        True: (
            PathCandidate(
                path="scripts",
                provenance=CandidateProvenance.DIRECTORY_SCAN,
                present=True,
            ),
        ),
    }[has_tooling]
    roots: tuple[PathCandidate, ...] = {
        True: (),
        False: (
            PathCandidate(
                path="src/pkg",
                provenance=CandidateProvenance.DIRECTORY_SCAN,
                present=True,
            ),
        ),
    }[is_empty]
    return DetectedRepositoryLayout(
        roots=roots,
        tests=(
            PathCandidate(
                path="tests",
                provenance=CandidateProvenance.DEFAULT_NOT_PRESENT,
                present=False,
            ),
        ),
        tooling=tooling,
        python=PythonState(
            file_count={False: 1, True: 0}[is_empty],
            package_count=0,
            is_empty=is_empty,
        ),
    )


def detected_nonempty_without_roots() -> DetectedRepositoryLayout:
    """Build a non-empty loose-Python layout with no runtime candidates."""

    detected: DetectedRepositoryLayout = detected_layout(is_empty=False, has_tooling=False)
    return DetectedRepositoryLayout(
        roots=(),
        tests=detected.tests,
        tooling=detected.tooling,
        python=detected.python,
    )


def init_options(*, test_case: InteractionDecisionTestCase) -> InitOptions:
    """Translate an interaction case into runtime options."""

    return InitOptions(
        yes=test_case.yes,
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
        skills=test_case.skills,
        name=test_case.name,
    )


def prepare_execution_failure(*, root: Path, test_case: ExecutionFailureTestCase) -> None:
    """Create any pre-existing path that should force transactional refusal."""

    directories: filter[str] = filter(None, (test_case.blocking_directory,))
    for directory in directories:
        (root / directory).mkdir(parents=True)


def present_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that currently exist."""

    return tuple(filter(lambda path: (root / path).exists(), paths))


def absent_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that currently do not exist."""

    return tuple(filter(lambda path: not (root / path).exists(), paths))


def file_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that are regular files."""

    return tuple(filter(lambda path: (root / path).is_file(), paths))


def applicability_options(*, test_case: OptionApplicabilityTestCase) -> InitOptions:
    """Build options from one applicability case."""

    return InitOptions(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
        name=test_case.name,
    )


def prepare_config_path(*, root: Path, path_kind: str) -> None:
    """Create a regular or broken-symlink config destination."""

    path: Path = root / "fensu.toml"
    create: Callable[[], object] = {
        "regular": lambda: path.write_text("existing = true\n", encoding="utf-8"),
        "broken-symlink": lambda: path.symlink_to(root / "missing-config-target"),
    }[path_kind]
    _ = create()


def config_temp_paths(*, root: Path) -> tuple[str, ...]:
    """Return atomic config temporary files left in a repository."""

    return tuple(path.name for path in sorted(root.glob(".fensu.toml.*.tmp")))


def prepare_scaffold_symlink(*, root: Path, test_case: ScaffoldSymlinkTestCase) -> None:
    """Create a symlink in the source or test scaffold path."""

    outside: Path = root / "outside"
    outside.mkdir()

    def create_package_symlink() -> None:
        (root / "src").mkdir()
        (root / "src/pkg").symlink_to(outside, target_is_directory=True)

    def create_test_symlink() -> None:
        (root / "tests").symlink_to(outside, target_is_directory=True)

    create: Callable[[], None] = {
        "package": create_package_symlink,
        "tests": create_test_symlink,
    }[test_case.symlink_kind]
    create()


def symlink_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that remain symlinks, including broken links."""

    return tuple(filter(lambda path: (root / path).is_symlink(), paths))


def lexisting_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return paths that exist without following their final symlink."""

    return tuple(filter(lambda path: os.path.lexists(root / path), paths))


def config_destination_kind(*, root: Path) -> str:
    """Describe the config destination without following a symlink."""

    path: Path = root / "fensu.toml"
    return {
        (False, False): "missing",
        (False, True): "regular",
        (True, False): "symlink",
        (True, True): "symlink",
    }[(path.is_symlink(), path.is_file())]


def config_destination_value(*, root: Path) -> str:
    """Read the racing destination without following symlinks unexpectedly."""

    path: Path = root / "fensu.toml"
    read: Callable[[], str] = {
        False: lambda: path.read_text(encoding="utf-8"),
        True: lambda: os.readlink(path),
    }[path.is_symlink()]
    return read()


def invoke_prompt(*, prompt_kind: str, input_text: str) -> bool | tuple[str, ...] | str:
    """Invoke one defaulted prompt with controlled input."""

    stdin: StringIO = StringIO(input_text)
    stdout: StringIO = StringIO()
    style: CliStyle = CliStyle(use_color=False)
    candidates: tuple[PathCandidate, ...] = (
        PathCandidate(
            path="src/alpha",
            provenance=CandidateProvenance.DIRECTORY_SCAN,
            present=True,
        ),
        PathCandidate(
            path="src/beta",
            provenance=CandidateProvenance.DIRECTORY_SCAN,
            present=True,
        ),
    )
    prompts: dict[str, Callable[[], bool | tuple[str, ...] | str]] = {
        "generic": lambda: prompt_yes_no(
            stdin=stdin, stdout=stdout, style=style, prompt="Continue?"
        ),
        "layout": lambda: prompt_accept_layout(stdin=stdin, stdout=stdout, style=style),
        "root": lambda: prompt_root_selection(
            stdin=stdin, stdout=stdout, style=style, candidates=candidates
        ),
        "name": lambda: prompt_project_name(
            stdin=stdin, stdout=stdout, style=style, repository_name="my-project"
        ),
    }
    return prompts[prompt_kind]()


def prepare_scope_python_symlink(*, root: Path, test_case: ScopeSymlinkTestCase) -> None:
    """Create valid selected scopes with one Python symlink."""

    build_repository(root=root, files=(("src/pkg/__init__.py", ""),))
    target: Path = root / "outside.py"
    target.write_text("value: int = 1\n", encoding="utf-8")
    symlink: Path = root / test_case.symlink_path
    symlink.parent.mkdir(parents=True, exist_ok=True)
    symlink.symlink_to(target)


def prepare_metadata_marker_symlink(*, root: Path, marker_path: str) -> None:
    """Create a package directory whose marker is a symlink."""

    target: Path = root / "marker-target.py"
    target.write_text("", encoding="utf-8")
    marker: Path = root / marker_path
    marker.parent.mkdir(parents=True)
    marker.symlink_to(target)
