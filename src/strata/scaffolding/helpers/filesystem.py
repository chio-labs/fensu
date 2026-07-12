"""Conservative filesystem signals for repository layout detection."""

from __future__ import annotations

import os
from pathlib import Path

from strata.scaffolding.constants import (
    EXCLUDED_DIRECTORY_NAMES,
    PACKAGE_MARKER_FILE_NAME,
    PYTHON_FILE_SUFFIX,
    SOURCE_CONTAINER_NAMES,
    TOOLING_DIRECTORY_NAMES,
)
from strata.scaffolding.helpers.gitignore import build_gitignore_predicate
from strata.scaffolding.models import PythonState
from strata.scaffolding.types import (
    CandidateInput,
    CandidateProvenance,
    GitIgnorePredicate,
)


def filesystem_root_inputs(*, repository: Path) -> tuple[CandidateInput, ...]:
    """Find package directories only at the plan's deterministic fallback depths."""

    ignored: GitIgnorePredicate = build_gitignore_predicate(repository=repository)
    roots: list[Path] = []
    roots.extend(_fallback_package_children(container=repository, ignored=ignored))
    for name in SOURCE_CONTAINER_NAMES:
        roots.extend(_fallback_package_children(container=repository / name, ignored=ignored))
    packages: Path = repository / "packages"
    if packages.is_dir() and not packages.is_symlink():
        for member in sorted(packages.iterdir(), key=lambda path: path.name):
            if member.is_dir() and not member.is_symlink():
                roots.extend(_fallback_package_children(container=member / "src", ignored=ignored))
    return tuple((path, CandidateProvenance.DIRECTORY_SCAN) for path in roots)


def tooling_inputs(*, repository: Path) -> tuple[CandidateInput, ...]:
    """Find conventional tooling directories that contain Python files."""

    ignored: GitIgnorePredicate = build_gitignore_predicate(repository=repository)
    inputs: list[CandidateInput] = []
    for name in TOOLING_DIRECTORY_NAMES:
        path: Path = repository / name
        if (
            not path.is_symlink()
            and path.is_dir()
            and not ignored(path=path, is_directory=True)
            and _contains_python(path=path, ignored=ignored)
        ):
            inputs.append((path, CandidateProvenance.DIRECTORY_SCAN))
    return tuple(inputs)


def inspect_python_state(*, repository: Path) -> PythonState:
    """Count Python files and package markers outside fixed excluded directories."""

    ignored: GitIgnorePredicate = build_gitignore_predicate(repository=repository)
    files: tuple[Path, ...] = _python_files(path=repository, ignored=ignored)
    package_count: int = sum(path.name == PACKAGE_MARKER_FILE_NAME for path in files)
    file_count: int = len(files)
    return PythonState(
        file_count=file_count,
        package_count=package_count,
        is_empty=package_count == 0,
    )


def package_children(*, container: Path) -> tuple[Path, ...]:
    """Return deterministic immediate package children of a metadata container."""

    return tuple(_package_children(container=container))


def _package_children(*, container: Path) -> list[Path]:
    packages: list[Path] = []
    if container.is_symlink() or not container.is_dir():
        return packages
    for child in sorted(container.iterdir(), key=lambda path: path.name):
        if child.name in EXCLUDED_DIRECTORY_NAMES or child.is_symlink():
            continue
        marker: Path = child / PACKAGE_MARKER_FILE_NAME
        if child.is_dir() and not marker.is_symlink() and marker.is_file():
            packages.append(child)
    return packages


def _fallback_package_children(*, container: Path, ignored: GitIgnorePredicate) -> list[Path]:
    return [
        path
        for path in _package_children(container=container)
        if not ignored(path=path, is_directory=True)
        and not ignored(path=path / PACKAGE_MARKER_FILE_NAME, is_directory=False)
    ]


def _contains_python(*, path: Path, ignored: GitIgnorePredicate) -> bool:
    return bool(_python_files(path=path, ignored=ignored))


def _python_files(*, path: Path, ignored: GitIgnorePredicate) -> tuple[Path, ...]:
    discovered: list[Path] = []
    resolved_root: Path = path.resolve()
    for current_text, directories, files in os.walk(path, followlinks=False):
        current: Path = Path(current_text)
        directories[:] = sorted(
            name
            for name in directories
            if name not in EXCLUDED_DIRECTORY_NAMES and not (current / name).is_symlink()
        )
        for name in sorted(files):
            candidate: Path = current / name
            if candidate.suffix != PYTHON_FILE_SUFFIX or candidate.is_symlink():
                continue
            if ignored(path=candidate, is_directory=False):
                continue
            try:
                candidate.resolve().relative_to(resolved_root)
            except ValueError:
                continue
            discovered.append(candidate)
    return tuple(discovered)
