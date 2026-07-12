"""Scaffolding type-layer declarations."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol


class CandidateProvenance(StrEnum):
    """Stable user-facing explanation for a detected path."""

    HATCH_PACKAGES = "pyproject: hatch packages"
    SETUPTOOLS_FIND = "pyproject: setuptools find.where"
    SETUPTOOLS_PACKAGE_DIR = "pyproject: setuptools package-dir"
    POETRY_PACKAGES = "pyproject: poetry packages"
    FLIT_MODULE = "pyproject: flit module name"
    UV_WORKSPACE = "pyproject: uv workspace member"
    PROJECT_NAME = "pyproject: project name"
    RUFF_SRC = "ruff src"
    PYTEST_TESTPATHS = "pytest testpaths"
    COMMAND_LINE = "command line"
    DIRECTORY_SCAN = "directory scan"
    DEFAULT_NOT_PRESENT = "not present yet"


class AdoptionMode(StrEnum):
    """Starting ruleset selected for a repository."""

    FULL = "full"
    GRADUAL = "gradual"


class InteractionDecision(StrEnum):
    """Whether init can proceed without reading terminal input."""

    NON_INTERACTIVE = "non-interactive"
    TTY_REQUIRED = "tty-required"


type CandidateInput = tuple[Path, CandidateProvenance]


class GitIgnorePredicate(Protocol):
    """Repository-bound ignore decision used during one detection pass."""

    def __call__(self, *, path: Path, is_directory: bool) -> bool:
        """Return whether root ignore rules exclude a path."""
        ...
