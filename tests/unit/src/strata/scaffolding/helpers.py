"""Local filesystem helpers for scaffolding tests."""

from __future__ import annotations

import os
from collections.abc import Callable
from io import StringIO
from pathlib import Path

from strata.reporting.classes.cli_style import CliStyle
from strata.scaffolding.helpers.output import (
    prompt_accept_layout,
    prompt_project_name,
    prompt_root_selection,
    prompt_yes_no,
)
from strata.scaffolding.models import (
    DetectedRepositoryLayout,
    InitOptions,
    PathCandidate,
    PythonState,
)
from strata.scaffolding.types import CandidateProvenance
from tests.unit.src.strata.scaffolding._test_types import (
    DetectionTestCase,
    ExecutionFailureTestCase,
    InteractionDecisionTestCase,
    OptionApplicabilityTestCase,
    ScaffoldSymlinkTestCase,
    ScopeSymlinkTestCase,
)


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

    tooling: tuple[PathCandidate, ...] = ()
    if has_tooling:
        tooling = (
            PathCandidate(
                path="scripts",
                provenance=CandidateProvenance.DIRECTORY_SCAN,
                present=True,
            ),
        )
    roots: tuple[PathCandidate, ...] = ()
    if not is_empty:
        roots = (
            PathCandidate(
                path="src/pkg",
                provenance=CandidateProvenance.DIRECTORY_SCAN,
                present=True,
            ),
        )
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
        python=PythonState(file_count=0 if is_empty else 1, package_count=0, is_empty=is_empty),
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

    if test_case.blocking_directory is not None:
        (root / test_case.blocking_directory).mkdir(parents=True)


def present_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that currently exist."""

    return tuple(path for path in paths if (root / path).exists())


def absent_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that currently do not exist."""

    return tuple(path for path in paths if not (root / path).exists())


def file_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that are regular files."""

    return tuple(path for path in paths if (root / path).is_file())


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

    path: Path = root / "strata.toml"
    if path_kind == "regular":
        path.write_text("existing = true\n", encoding="utf-8")
        return
    path.symlink_to(root / "missing-config-target")


def config_temp_paths(*, root: Path) -> tuple[str, ...]:
    """Return atomic config temporary files left in a repository."""

    return tuple(path.name for path in sorted(root.glob(".strata.toml.*.tmp")))


def temp_unlink_failure(*, original: Callable[..., None]) -> Callable[..., None]:
    """Return a Path.unlink replacement that fails only for config temporaries."""

    def unlink(path: Path, missing_ok: bool = False) -> None:
        if path.name.startswith(".strata.toml.") and path.suffix == ".tmp":
            raise OSError("temporary config cleanup failed")
        original(path, missing_ok=missing_ok)

    return unlink


def temp_aliases_config(*, root: Path) -> bool:
    """Return whether every remaining config temporary aliases the published inode."""

    config: Path = root / "strata.toml"
    temporaries: tuple[Path, ...] = tuple(sorted(root.glob(".strata.toml.*.tmp")))
    return bool(temporaries) and all(temp.samefile(config) for temp in temporaries)


def fail_atomic_link(source: Path, destination: Path, *, follow_symlinks: bool = True) -> None:
    """Model publication failure before the config hard link exists."""

    _ = (source, destination, follow_symlinks)
    raise OSError("config hard-link publication failed")


def prepare_scaffold_symlink(*, root: Path, test_case: ScaffoldSymlinkTestCase) -> None:
    """Create a symlink in the source or test scaffold path."""

    outside: Path = root / "outside"
    outside.mkdir()
    if test_case.symlink_kind == "package":
        (root / "src").mkdir()
        (root / "src/pkg").symlink_to(outside, target_is_directory=True)
        return
    (root / "tests").symlink_to(outside, target_is_directory=True)


def symlink_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return declared paths that remain symlinks, including broken links."""

    return tuple(path for path in paths if (root / path).is_symlink())


def lexisting_paths(*, root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return paths that exist without following their final symlink."""

    return tuple(path for path in paths if os.path.lexists(root / path))


def atomic_link_racer(*, destination_kind: str) -> Callable[..., None]:
    """Return an os.link replacement that creates a racing destination."""

    return _race_file_link if destination_kind == "regular" else _race_symlink_link


def config_destination_kind(*, root: Path) -> str:
    """Describe the config destination without following a symlink."""

    path: Path = root / "strata.toml"
    if path.is_symlink():
        return "symlink"
    if path.is_file():
        return "regular"
    return "missing"


def config_destination_value(*, root: Path) -> str:
    """Read the racing destination without following symlinks unexpectedly."""

    path: Path = root / "strata.toml"
    if path.is_symlink():
        return os.readlink(path)
    return path.read_text(encoding="utf-8")


def invoke_prompt(*, prompt_kind: str, input_text: str) -> bool | tuple[str, ...] | str:
    """Invoke one defaulted prompt with controlled input."""

    stdin: StringIO = StringIO(input_text)
    stdout: StringIO = StringIO()
    style: CliStyle = CliStyle(use_color=False)
    if prompt_kind == "generic":
        return prompt_yes_no(stdin=stdin, stdout=stdout, style=style, prompt="Continue?")
    if prompt_kind == "layout":
        return prompt_accept_layout(stdin=stdin, stdout=stdout, style=style)
    if prompt_kind == "root":
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
        return prompt_root_selection(stdin=stdin, stdout=stdout, style=style, candidates=candidates)
    return prompt_project_name(
        stdin=stdin, stdout=stdout, style=style, repository_name="my-project"
    )


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


def _race_file_link(source: Path, destination: Path, *, follow_symlinks: bool = True) -> None:
    _ = (source, follow_symlinks)
    destination.write_text("racing config\n", encoding="utf-8")
    raise FileExistsError(destination)


def _race_symlink_link(source: Path, destination: Path, *, follow_symlinks: bool = True) -> None:
    _ = (source, follow_symlinks)
    destination.symlink_to("racing-target")
    raise FileExistsError(destination)
