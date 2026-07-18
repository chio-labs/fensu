"""Test case types for native Strata Memory integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeMemoryQueryTestCase:
    """One enabled temporary project and expected native query result."""

    description: str
    sql: str
    expected_columns: tuple[str, ...]
    expected_rows: tuple[tuple[object, ...], ...]
    expected_database_relative_path: str


@dataclass(frozen=True)
class NativeMemoryErrorTestCase:
    """One rejected native query and expected stable domain error."""

    description: str
    sql: str
    expected_error_fragment: str
    expected_stdout: str
    expected_exit_code: int


@dataclass(frozen=True)
class NativeMemorySchemaTestCase:
    """One focused schema request that must not create a database."""

    description: str
    relation: str
    expected_relation: str
    expected_database_exists: bool


@dataclass(frozen=True)
class NativeMemoryColorTestCase:
    """One human CLI format and its expected ANSI behavior."""

    description: str
    argv: tuple[str, ...]
    expected_stdout_fragment: str
    expected_absent_fragment: str
    expected_exit_code: int


@dataclass(frozen=True)
class NativeMemoryCheckTestCase:
    """One invalid canonical source and its direct native check response."""

    description: str
    relative_path: str
    contents: str
    expected_fault_fragment: str
    expected_database_exists: bool
    expected_exit_code: int


@dataclass(frozen=True)
class NativeMemoryArchiveTestCase:
    """One explicit source and expected archive CLI publication."""

    description: str
    relative_path: str
    contents: str
    expected_destination: str
    expected_output_fragment: str
    expected_exit_code: int
