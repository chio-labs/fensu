"""Detect deterministic candidates for a repository's Fensu layout."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fensu.scaffolding._helpers.candidates import ordered_candidates
from fensu.scaffolding._helpers.filesystem import (
    filesystem_root_inputs,
    inspect_python_state,
    tooling_inputs,
)
from fensu.scaffolding._helpers.gitignore import build_gitignore_predicate
from fensu.scaffolding._helpers.pyproject import (
    load_pyproject,
    metadata_root_inputs,
    pytest_inputs,
)
from fensu.scaffolding.constants import (
    DEFAULT_TEST_PATH,
    PACKAGE_MARKER_FILE_NAME,
    TEST_DIRECTORY_NAMES,
)
from fensu.scaffolding.exceptions import RepositoryDetectionError
from fensu.scaffolding.models import DetectedRepositoryLayout, PathCandidate, PythonState
from fensu.scaffolding.types import (
    CandidateInput,
    CandidateProvenance,
    GitIgnorePredicate,
)


def detect_repository_layout(*, repository: Path) -> DetectedRepositoryLayout:
    """Detect ordered roots, tests, tooling, and Python state without guessing."""

    resolved_repository: Path = repository.resolve()
    if not resolved_repository.is_dir():
        raise RepositoryDetectionError(f"Repository directory does not exist: {repository}")
    pyproject: Mapping[str, object] = load_pyproject(repository=resolved_repository)
    root_inputs: tuple[CandidateInput, ...] = (
        *metadata_root_inputs(repository=resolved_repository, data=pyproject),
        *filesystem_root_inputs(repository=resolved_repository),
    )
    roots: tuple[PathCandidate, ...] = ordered_candidates(
        repository=resolved_repository, inputs=root_inputs
    )
    tests: tuple[PathCandidate, ...] = _detect_tests(
        repository=resolved_repository, pyproject=pyproject
    )
    tooling: tuple[PathCandidate, ...] = ordered_candidates(
        repository=resolved_repository,
        inputs=tooling_inputs(repository=resolved_repository),
    )
    tooling_paths: frozenset[str] = frozenset(candidate.path for candidate in tooling)
    roots = tuple(candidate for candidate in roots if candidate.path not in tooling_paths)
    _validate_package_markers(repository=resolved_repository, roots=roots)
    inspected: PythonState = inspect_python_state(repository=resolved_repository)
    python: PythonState = PythonState(
        file_count=inspected.file_count,
        package_count=inspected.package_count,
        is_empty=inspected.package_count == 0 and not roots,
    )
    return DetectedRepositoryLayout(roots=roots, tests=tests, tooling=tooling, python=python)


def _detect_tests(
    *, repository: Path, pyproject: Mapping[str, object]
) -> tuple[PathCandidate, ...]:
    inputs: list[CandidateInput] = list(pytest_inputs(repository=repository, data=pyproject))
    ignored: GitIgnorePredicate = build_gitignore_predicate(repository=repository)
    for name in TEST_DIRECTORY_NAMES:
        path: Path = repository / name
        if not path.is_symlink() and path.is_dir() and not ignored(path=path, is_directory=True):
            inputs.append((path, CandidateProvenance.DIRECTORY_SCAN))
    if not inputs:
        return (
            PathCandidate(
                path=DEFAULT_TEST_PATH,
                provenance=CandidateProvenance.DEFAULT_NOT_PRESENT,
                present=False,
            ),
        )
    return ordered_candidates(repository=repository, inputs=tuple(inputs), allow_absent=True)


def _validate_package_markers(*, repository: Path, roots: tuple[PathCandidate, ...]) -> None:
    for candidate in roots:
        marker: Path = repository / candidate.path / PACKAGE_MARKER_FILE_NAME
        if marker.is_symlink():
            raise RepositoryDetectionError(
                f"Detected package marker must not be a symlink: {marker}"
            )
