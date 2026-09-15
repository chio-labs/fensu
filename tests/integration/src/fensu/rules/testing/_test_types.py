"""Test case types for the public custom-rule harness."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fensu import RuleCase


@dataclass(frozen=True)
class HarnessEvaluationTestCase:
    """A real-pipeline harness input and its expected public result."""

    description: str
    rule: Any
    rule_case: RuleCase
    expected_fault_count: int
    expected_lines: tuple[int | None, ...]
    expected_messages: tuple[str, ...]
    rule_options: Mapping[str, object] | None = None
    expected_dependency_paths: tuple[str, ...] = ()
    expected_python_parse_count: int = 0


@dataclass(frozen=True)
class HarnessMisuseTestCase:
    """An invalid harness input and its stable error contract."""

    description: str
    rule: Any
    rule_case: Any
    expected_error_type: type[Exception]
    expected_error_fragment: str
    rule_options: Mapping[str, object] | None = None


@dataclass(frozen=True)
class FrozenHarnessModelTestCase:
    """A public harness model and the expected frozen assignment failure."""

    description: str
    model: object
    field_name: str
    expected_error_type: type[Exception]


@dataclass(frozen=True, slots=True)
class TypedFileSubjectTestCase:
    """Typed file-rule input and expected rule metadata."""

    description: str
    rule_case: RuleCase
    expected_fault_count: int
    expected_subject_kind: str
    expected_subject_parameter: str
    expected_context_parameter: str


@dataclass(frozen=True, slots=True)
class TypedProjectSubjectTestCase:
    """Typed project-rule input and expected aggregate observations."""

    description: str
    rule_case: RuleCase
    expected_fault_count: int
    expected_path: Path
    expected_message: str
    expected_dependency_count: int
    expected_requesters: frozenset[Path]
    expected_dependency_kinds: frozenset[str]


@dataclass(frozen=True, slots=True)
class EmptyProjectSubjectTestCase:
    """Empty discovered project and its expected project-rule outcome."""

    description: str
    expected_file_count: int
    expected_fault_count: int
    expected_fault_path: str


@dataclass(frozen=True, slots=True)
class InvalidProjectPathTestCase:
    """One unconfined path value and its expected validation detail."""

    description: str
    value: str
    expected_error_fragment: str


@dataclass(frozen=True, slots=True)
class TypedRuleFailureTestCase:
    """One invalid typed-rule evaluation and its expected exception."""

    description: str
    rule_case: RuleCase
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True, slots=True)
class ProjectWarningTestCase:
    """Empty project warning evaluation and its expected result counts."""

    description: str
    expected_fault_count: int
    expected_warning_count: int


@dataclass(frozen=True, slots=True)
class ProjectExceptionTestCase:
    """Project exception input and its expected suppressed fault count."""

    description: str
    rule_case: RuleCase
    expected_fault_count: int


@dataclass(frozen=True, slots=True)
class ConflictingOwnerTestCase:
    """Conflicting typed owner declaration and its expected definition error."""

    description: str
    expected_error_fragment: str
