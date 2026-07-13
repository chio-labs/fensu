"""Test case types for CLI end-to-end coverage."""

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
class InstalledEntryCliTestCase:
    """Top-level installed CLI arguments and expected process output."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_stdout: str
    expected_stderr: str


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


@dataclass(frozen=True)
class CacheCliTestCase:
    """Installed CLI cache modes and expected process/storage behavior."""

    description: str
    config: str
    files: tuple[CliProjectFile, ...]
    expected_exit_code: int
    expected_stdout_fragment: str
    expected_cache_exists: bool


@dataclass(frozen=True)
class CacheMutationCliTestCase:
    """Installed CLI source mutation and expected invalidated output."""

    description: str
    config: str
    relative_path: str
    first_source: str
    second_source: str
    expected_exit_code: int
    expected_first_fragment: str
    expected_second_fragment: str


@dataclass(frozen=True)
class CacheManifestCliTestCase:
    """Installed CLI manifest mutation and expected complete diagnostics."""

    description: str
    config: str
    initial_paths: tuple[str, ...]
    final_paths: tuple[str, ...]
    expected_exit_code: int
    expected_present_paths: tuple[str, ...]
    expected_absent_paths: tuple[str, ...]


@dataclass(frozen=True)
class CacheDependencyCliTestCase:
    """Installed CLI negative dependency creation and expected diagnostics."""

    description: str
    config: str
    requester_path: str
    requester_source: str
    dependency_path: str
    dependency_source: str
    expected_first_exit_code: int
    expected_second_exit_code: int
    expected_first_fragment: str
    expected_second_fragment: str


@dataclass(frozen=True)
class InstalledInitCliTestCase:
    """Installed init invocation and expected repository and process state."""

    description: str
    argv: tuple[str, ...]
    input_text: str
    initial_files: tuple[CliProjectFile, ...]
    expected_exit_code: int
    expected_files: tuple[CliProjectFile, ...]
    expected_config_values: tuple[tuple[str, tuple[str, ...]], ...]
    expected_stdout_fragments: tuple[str, ...]
    expected_stderr_fragments: tuple[str, ...]
    expected_absent_output_fragments: tuple[str, ...]
    expected_stdout_is_empty: bool
