"""Test case types for the public custom-rule harness."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
