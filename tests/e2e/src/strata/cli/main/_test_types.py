"""Test case types for configurable-layout CLI end-to-end coverage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CliProjectFile:
    """One repository-relative fixture file."""

    relative_path: str
    source: str
    description: str = "project fixture file"
    expected_written: bool = True


@dataclass(frozen=True)
class ConfigurableLayoutCliTestCase:
    """A complete temporary project and expected CLI process result."""

    description: str
    config: str
    files: tuple[CliProjectFile, ...]
    working_directory: str
    expected_exit_code: int
    expected_stdout_fragments: tuple[str, ...]
    expected_stderr_fragments: tuple[str, ...]
    argv: tuple[str, ...] = ("check", "--no-color")
