"""Evaluation runtime protocols."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol

from fensu.analysis.types import ProjectAnalysis
from fensu.discovery.models import ScopedFile
from fensu.evaluation.models import ParsedModule
from fensu.rules.authoring.models import Fault

type NativeFaultRow = tuple[str, str | None, int | None, int | None, str | None, str | None]
type NativeFaultsByCode = dict[str, tuple[Fault, ...]]
type NativeThresholdValues = dict[str, int]
type NativeRuleOptionValues = dict[str, dict[str, str]]
type NativeExecutionRequest = tuple[
    str,
    list[str],
    str,
    str | None,
    bool,
    NativeThresholdValues,
    str,
    list[tuple[str, str]],
    list[str],
    bool,
    str,
    tuple[
        list[str],
        list[tuple[str, str]],
        dict[str, list[str]],
        list[tuple[str, str, str, str, int, int]],
        str,
        NativeRuleOptionValues,
    ],
]
type NativeProjectFile = tuple[str, str, list[str], str]


class NativeProjectQueryKind(StrEnum):
    """Project observations requested by native FILE rules."""

    EXISTS = "exists"
    IS_FILE = "is_file"
    IS_DIR = "is_dir"
    DATACLASSES = "dataclasses"
    MODULE_FUNCTION = "module_function"
    PACKAGE_ANCHOR = "package_anchor"
    CUSTOM_RULE_COVERAGE = "custom_rule_coverage"
    DIRECTORY_ENTRIES = "directory_entries"
    GLOB = "glob"
    PYTHON_ANCHOR = "python_anchor"


class EvaluationProjectAnalysis(ProjectAnalysis, Protocol):
    """Project analysis with strict discovered-file parsing for evaluation."""

    def parsed_module(self, scoped_file: ScopedFile) -> ParsedModule:
        """Return one strict discovered-file parse."""
        ...

    def prewarm(self, *, parsed: ParsedModule) -> None:
        """Adopt one pre-parsed discovered module for later single-use retrieval."""
        ...

    def native_source(self, *, requester: Path, path: Path) -> str | None:
        """Return decoded source while recording its source dependency without a CPython AST."""
        ...
