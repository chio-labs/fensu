"""Test case types for isolated CLI entry dispatch."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.scaffolding.models import InitOptions


@dataclass(frozen=True)
class EntryDispatchTestCase:
    """CLI argv and expected delegated command runner."""

    description: str
    argv: tuple[str, ...]
    runner_attribute: str
    expected_forwarded_argv: tuple[str, ...]
    expected_exit_code: int


@dataclass(frozen=True)
class EntryUsageTestCase:
    """Top-level CLI input and expected process response."""

    description: str
    argv: tuple[str, ...]
    expected_stdout: str
    expected_stderr: str
    expected_exit_code: int


@dataclass(frozen=True)
class EntryLazyImportTestCase:
    """One lightweight option and command module expected to remain unloaded."""

    description: str
    argv: tuple[str, ...]
    module_name: str
    expected_imported: bool


@dataclass(frozen=True)
class InitAdapterTestCase:
    """Init argv and expected core options."""

    description: str
    argv: tuple[str, ...]
    stdout_isatty: bool
    expected_options: InitOptions
    expected_use_color: bool
    expected_exit_code: int


@dataclass(frozen=True)
class InitNoColorTestCase:
    """Environment color override and expected core color choice."""

    description: str
    no_color: str
    expected_use_color: bool
    expected_exit_code: int


@dataclass(frozen=True)
class MemoryAdapterTestCase:
    """Memory CLI arguments and expected parser response."""

    description: str
    argv: tuple[str, ...]
    expected_stdout: str
    expected_stderr_fragment: str
    expected_exit_code: int


@dataclass(frozen=True)
class MemoryDisabledAdapterTestCase:
    """One memory command that must honor the project enablement gate."""

    description: str
    argv: tuple[str, ...]
    expected_error_fragment: str
    expected_database_exists: bool
    expected_exit_code: int
