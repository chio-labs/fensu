"""Tests for naming contract rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.exceptions import ConfigError
from strata.evaluation.models import EvaluationResult
from tests.unit.src.strata.rules.naming.main._test_types import (
    SfnConflictTestCase,
    SfnRuleTestCase,
)
from tests.unit.src.strata.rules.naming.main.helpers import evaluate_naming_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        SfnRuleTestCase(
            description="validator returning value is flagged",
            source="def validate_config() -> bool:\n    return True\n",
            expected_codes=("SFN001",),
            expected_lines=(2,),
            expected_message_fragments=("validate_config", "meaningful value"),
            expected_remediation_fragments=("Remove the meaningful return", "rename"),
        ),
        SfnRuleTestCase(
            description="validator returning None is allowed",
            source="def validate_config() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="validator bare return is allowed",
            source="def validate_config() -> None:\n    return\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="enforcer returning value is flagged",
            source="async def enforce_policy() -> int:\n    return 1\n",
            expected_codes=("SFN001",),
            expected_lines=(2,),
        ),
        SfnRuleTestCase(
            description="accepted predicate annotations and missing annotations are legal",
            source=(
                "from typing import TypeGuard\n"
                "from typing_extensions import TypeIs\n"
                "def is_ready() -> bool:\n    return True\n"
                "def has_items() -> builtins.bool:\n    return True\n"
                "def can_narrow(value: object) -> TypeGuard[int]:\n    return True\n"
                "def supports_narrow(value: object) -> typing_extensions.TypeIs[int]:\n"
                "    return True\n"
                "async def is_async() -> 'bool':\n    return True\n"
                "def has_missing():\n    return True\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="predicate annotations outside the exact accepted forms are flagged",
            source=(
                "def is_count() -> int:\n    return 1\n"
                "def has_status() -> Status:\n    return Status()\n"
                "def can_retry() -> bool | None:\n    return None\n"
                "def supports_mode() -> Literal[True]:\n    return True\n"
                "def is_done() -> None:\n    return None\n"
            ),
            expected_codes=("SFN002",) * 5,
            expected_lines=(1, 3, 5, 7, 9),
            expected_message_fragments=("is_count", "int", "has_status", "Status"),
            expected_remediation_fragments=("Return bool", "rename", "count_status"),
        ),
        SfnRuleTestCase(
            description="value names allow concrete optional raising and missing declarations",
            source=(
                "def get_user() -> User:\n    return User()\n"
                "def get_optional() -> User | None:\n    return None\n"
                "def get_legacy() -> Optional[User]:\n    return None\n"
                "def to_text() -> str:\n    return 'value'\n"
                "def as_record() -> Record:\n    raise LookupError\n"
                "def get_missing():\n    return object()\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="value names reject every explicit no-value annotation spelling",
            source=(
                "def get_user() -> None:\n    return None\n"
                "def to_user() -> NoReturn:\n    raise RuntimeError\n"
                "def as_user() -> typing.NoReturn:\n    raise RuntimeError\n"
                "def get_never() -> Never:\n    raise RuntimeError\n"
                "def to_never() -> 'typing.Never':\n    raise RuntimeError\n"
                "def as_none() -> 'None':\n    return None\n"
            ),
            expected_codes=("SFN003",) * 6,
            expected_lines=(1, 3, 5, 7, 9, 11),
            expected_message_fragments=("get_user", "None", "to_never", "typing.Never"),
            expected_remediation_fragments=("Return the queried value", "write_json", "rename"),
        ),
        SfnRuleTestCase(
            description="iterator names allow owned yields and exact iterator declarations",
            source=(
                "def iter_yield() -> Iterable[int]:\n    yield 1\n"
                "async def iter_async_yield():\n    yield 1\n"
                "def iter_items() -> Iterator[int]:\n    return iterator\n"
                "def iter_generated() -> Generator[int, None, None]:\n    return generator\n"
                "def iter_async_items() -> typing.AsyncIterator[int]:\n    return iterator\n"
                "def iter_async_generated() -> 'typing.AsyncGenerator[int, None]':\n"
                "    return generator\n"
                "def iter_delegated() -> collections.abc.Iterator[int]:\n    return iter(())\n"
                "def iter_unannotated():\n    yield from ()\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="iterator names reject eager iterable and no-value results",
            source=(
                "def iter_list() -> list[int]:\n    return []\n"
                "def iter_tuple() -> tuple[int, ...]:\n    return ()\n"
                "def iter_iterable() -> Iterable[int]:\n    return []\n"
                "def iter_none() -> None:\n    return None\n"
                "def iter_nested() -> list[int]:\n"
                "    def nested():\n        yield 1\n"
                "    return list(nested())\n"
                "def iter_missing():\n    return []\n"
            ),
            expected_codes=("SFN004",) * 5,
            expected_lines=(1, 3, 5, 7, 9),
            expected_message_fragments=("iter_list", "list[int]", "iter_nested"),
            expected_remediation_fragments=("Return an iterator", "collect_list", "rename"),
        ),
        SfnRuleTestCase(
            description="custom patterns support every behavior",
            source=(
                "def ensure_ready() -> int:\n    return 1\n"
                "def eligible() -> Status:\n    return Status()\n"
                "def fetch_user() -> None:\n    return None\n"
                "def stream_rows() -> list[int]:\n    return []\n"
            ),
            contracts={
                "ensure_*": "no-return",
                "eligible": "returns-bool",
                "fetch_*": "returns-value",
                "stream_*": "returns-iterator",
            },
            expected_codes=("SFN001", "SFN002", "SFN003", "SFN004"),
            expected_lines=(2, 3, 5, 7),
        ),
        SfnRuleTestCase(
            description="exact default pattern override changes the enforced behavior",
            source="def is_ready() -> None:\n    return None\n",
            contracts={"is_*": "returns-value"},
            expected_codes=("SFN003",),
            expected_lines=(1,),
        ),
        SfnRuleTestCase(
            description="same behavior overlap is deduplicated",
            source="def is_ready() -> Status:\n    return Status()\n",
            contracts={"*_ready": "returns-bool"},
            expected_codes=("SFN002",),
            expected_lines=(1,),
        ),
        SfnRuleTestCase(
            description="check returning bool is not contracted",
            source="def check_value() -> bool:\n    return True\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="nested helper return does not count for validator",
            source=(
                "def validate_config() -> None:\n"
                "    def build_value() -> int:\n"
                "        return 1\n"
                "    build_value()\n"
                "    return None\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="custom no-return writer returning value is flagged",
            source="def write_record() -> int:\n    return 1\n",
            contracts={"write_*": "no-return"},
            expected_codes=("SFN001",),
            expected_lines=(2,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_function_contracts_when_checking_returns_then_flags_meaningful_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfnRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_naming_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
    messages: str = "\n".join(fault.message for fault in result.faults)
    remediations: str = "\n".join(fault.remediation or "" for fault in result.faults)
    assert all(fragment in messages for fragment in test_case.expected_message_fragments)
    assert all(fragment in remediations for fragment in test_case.expected_remediation_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        SfnConflictTestCase(
            description="different overlapping behaviors fail in sorted pattern order",
            source="def is_ready() -> bool:\n    return True\n",
            contracts={"*_ready": "returns-value"},
            expected_error_type=ConfigError,
            expected_message=(
                "Conflicting contracts for function 'is_ready' at "
                "src/pkg/domain/core/_helpers/checks.py: '*_ready' (returns-value), "
                "'is_*' (returns-bool)."
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_conflicting_contracts_when_function_matches_then_raises_stable_config_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfnConflictTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type) as error:
        evaluate_naming_test_case(
            test_case=SfnRuleTestCase(
                description=test_case.description,
                source=test_case.source,
                contracts=test_case.contracts,
                expected_codes=(),
                expected_lines=(),
            ),
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
        )

    assert str(error.value) == test_case.expected_message
