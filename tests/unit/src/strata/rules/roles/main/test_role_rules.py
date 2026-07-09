"""Tests for roles rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.core.models import EvaluationResult
from strata.rules.authoring.types import Threshold
from tests.unit.src.strata.rules.roles.main._test_types import SfrRuleTestCase, SfrSupportFile
from tests.unit.src.strata.rules.roles.main.helpers import evaluate_role_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="runtime function in models role is flagged",
            rule_code="SFR001",
            relative_path="domain/core/models.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("SFR001",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="dataclass in models role is allowed",
            rule_code="SFR001",
            relative_path="domain/core/models.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Result:\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="runtime function in types role is flagged",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("SFR002",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="protocol in types role is allowed",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="type-checking imports-only block in types role is allowed",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source="if TYPE_CHECKING:\n    from domain.core.models import Result\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="non-import in type-checking block in types role is flagged",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source="if TYPE_CHECKING:\n    value: int = 1\n",
            expected_codes=("SFR002",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="type-checking block with else in types role is flagged",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source="if TYPE_CHECKING:\n    from domain.core.models import Result\nelse:\n    Result = object\n",
            expected_codes=("SFR002",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="class in constants role is flagged",
            rule_code="SFR003",
            relative_path="domain/core/constants.py",
            source="class Config:\n    value: int\n",
            expected_codes=("SFR003",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="assignment in constants role is allowed",
            rule_code="SFR003",
            relative_path="domain/core/constants.py",
            source="DEFAULT_VALUE: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="plain class in exceptions role is flagged",
            rule_code="SFR004",
            relative_path="domain/core/exceptions.py",
            source="class Result:\n    value: int\n",
            expected_codes=("SFR004",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="custom error in exceptions role is allowed",
            rule_code="SFR004",
            relative_path="domain/core/exceptions.py",
            source="class ConfigError(Exception):\n    pass\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_files_when_checking_content_then_flags_only_foreign_declarations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="dataclass outside models role is flagged",
            rule_code="SFR101",
            relative_path="domain/core/helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Result:\n"
                "    value: int\n"
            ),
            expected_codes=("SFR101",),
            expected_lines=(4,),
        ),
        SfrRuleTestCase(
            description="private dataclass outside models role is allowed",
            rule_code="SFR101",
            relative_path="domain/core/helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class _Result:\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="protocol outside types role is flagged",
            rule_code="SFR102",
            relative_path="domain/core/classes/service.py",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_codes=("SFR102",),
            expected_lines=(3,),
        ),
        SfrRuleTestCase(
            description="private protocol in helpers role is allowed",
            rule_code="SFR102",
            relative_path="domain/core/helpers/service.py",
            source="from typing import Protocol\n\nclass _Service(Protocol):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="public uppercase constant outside constants role is flagged",
            rule_code="SFR103",
            relative_path="domain/core/helpers/values.py",
            source="DEFAULT_VALUE: int = 1\n",
            expected_codes=("SFR103",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="private uppercase constant outside constants role is allowed",
            rule_code="SFR103",
            relative_path="domain/core/helpers/values.py",
            source="_DEFAULT_VALUE: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="custom error outside exceptions role is flagged",
            rule_code="SFR104",
            relative_path="domain/core/helpers/errors.py",
            source="class ConfigError(Exception):\n    pass\n",
            expected_codes=("SFR104",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="plain class outside exceptions role is allowed",
            rule_code="SFR104",
            relative_path="domain/core/classes/result.py",
            source="class Result:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_declarations_when_checking_ownership_then_flags_only_misplaced_roles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="misc filename is flagged",
            rule_code="SFR201",
            relative_path="domain/core/helpers/misc.py",
            source="value: int = 1\n",
            expected_codes=("SFR201",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="common filename inside an owned role is allowed",
            rule_code="SFR201",
            relative_path="domain/core/helpers/common.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="shared domain package is flagged",
            rule_code="SFR204",
            relative_path="shared/core/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="common domain package is flagged",
            rule_code="SFR204",
            relative_path="common/core/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="util domain package is flagged",
            rule_code="SFR204",
            relative_path="util/core/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="utils subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/utils/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="misc subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/misc/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="base subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/base/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="lib subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/lib/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="generic package name inside helpers role is allowed",
            rule_code="SFR204",
            relative_path="domain/core/helpers/utils/value.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="domain-specific package names are allowed",
            rule_code="SFR204",
            relative_path="orders/compile/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="helpers module filename is flagged",
            rule_code="SFR202",
            relative_path="domain/core/helpers.py",
            source="value: int = 1\n",
            expected_codes=("SFR202",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="classes module filename is flagged",
            rule_code="SFR203",
            relative_path="domain/core/classes.py",
            source="class Service:\n    value: int\n",
            expected_codes=("SFR203",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="public plain class in helpers is flagged",
            rule_code="SFR205",
            relative_path="domain/core/helpers/service.py",
            source="class Service:\n    value: int\n",
            expected_codes=("SFR205",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="private plain class in helpers is allowed",
            rule_code="SFR205",
            relative_path="domain/core/helpers/service.py",
            source="class _Service:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="plain class in classes role is unaffected",
            rule_code="SFR205",
            relative_path="domain/core/classes/service.py",
            source="class Service:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="public dataclass in helpers is left to model ownership rule",
            rule_code="SFR205",
            relative_path="domain/core/helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Result:\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_names_and_helper_classes_when_checking_then_flags_only_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="module-level standalone call is flagged",
            rule_code="SFR206",
            relative_path="domain/core/helpers/startup.py",
            source="register_plugins()\n",
            expected_codes=("SFR206",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="assigned constructor call is allowed",
            rule_code="SFR206",
            relative_path="domain/core/helpers/logging.py",
            source="LOGGER: object = get_logger()\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="call inside function body is allowed",
            rule_code="SFR206",
            relative_path="domain/core/helpers/startup.py",
            source="def start() -> None:\n    register_plugins()\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="standalone call in class body is flagged",
            rule_code="SFR206",
            relative_path="domain/core/classes/service.py",
            source="class Service:\n    register_plugins()\n",
            expected_codes=("SFR206",),
            expected_lines=(2,),
        ),
        SfrRuleTestCase(
            description="call inside class method body is allowed",
            rule_code="SFR206",
            relative_path="domain/core/classes/service.py",
            source="class Service:\n    def start(self) -> None:\n        register_plugins()\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="conditional import-time call is flagged",
            rule_code="SFR206",
            relative_path="domain/core/helpers/startup.py",
            source="if enabled:\n    register_plugins()\n",
            expected_codes=("SFR206",),
            expected_lines=(2,),
        ),
        SfrRuleTestCase(
            description="type-checking guarded call is not executed at import",
            rule_code="SFR206",
            relative_path="domain/core/helpers/startup.py",
            source="if TYPE_CHECKING:\n    register_type_adapter()\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="main-guarded call is not executed during import",
            rule_code="SFR206",
            relative_path="domain/core/helpers/startup.py",
            source="if __name__ == '__main__':\n    main()\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_runtime_calls_when_checking_import_time_then_flags_executed_standalone_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="helpers package mixing modules and subfolders is flagged",
            rule_code="SFR301",
            relative_path="domain/core/helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="flat helper",
                    relative_path="domain/core/helpers/values.py",
                    source="value: int = 1\n",
                ),
                SfrSupportFile(
                    description="helper concern",
                    relative_path="domain/core/helpers/parsing/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("SFR301",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="helpers package over flat threshold is flagged",
            rule_code="SFR301",
            relative_path="domain/core/helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="first helper",
                    relative_path="domain/core/helpers/first.py",
                    source="value: int = 1\n",
                ),
                SfrSupportFile(
                    description="second helper",
                    relative_path="domain/core/helpers/second.py",
                    source="value: int = 2\n",
                ),
            ),
            thresholds={Threshold.MAX_FLAT_HELPER_MODULES: 1},
            expected_codes=("SFR301",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="flat helpers package under threshold is allowed",
            rule_code="SFR301",
            relative_path="domain/core/helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="flat helper",
                    relative_path="domain/core/helpers/values.py",
                    source="value: int = 1\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="main support folder is flagged",
            rule_code="SFR302",
            relative_path="domain/core/main/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR302",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="nested direct support module is flagged",
            rule_code="SFR304",
            relative_path="domain/core/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR304",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="nested role module is allowed",
            rule_code="SFR304",
            relative_path="domain/core/models.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="arbitrary nested direct subpackage is flagged",
            rule_code="SFR305",
            relative_path="domain/core/feature/__init__.py",
            source="",
            expected_codes=("SFR305",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="nested direct subpackage without init is flagged",
            rule_code="SFR305",
            relative_path="domain/core/feature/implementation.py",
            source="value: int = 1\n",
            expected_codes=("SFR305",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="nested helpers subpackage is allowed",
            rule_code="SFR305",
            relative_path="domain/core/helpers/parsing.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="role file directly under domain is flagged",
            rule_code="SFR306",
            relative_path="domain/models.py",
            source="",
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="role package without init directly under domain is flagged",
            rule_code="SFR306",
            relative_path="domain/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="classes package without init directly under domain is flagged",
            rule_code="SFR306",
            relative_path="domain/classes/service.py",
            source="class Service:\n    pass\n",
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="models package without init directly under domain is flagged",
            rule_code="SFR306",
            relative_path="domain/models/result.py",
            source="value: int = 1\n",
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="types package without init directly under domain is flagged",
            rule_code="SFR306",
            relative_path="domain/types/protocol.py",
            source="value: int = 1\n",
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="constants package without init directly under domain is flagged",
            rule_code="SFR306",
            relative_path="domain/constants/defaults.py",
            source="VALUE: int = 1\n",
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="exceptions package without init directly under domain is flagged",
            rule_code="SFR306",
            relative_path="domain/exceptions/config.py",
            source="class ConfigError(Exception):\n    pass\n",
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="role file below subpackage is allowed",
            rule_code="SFR306",
            relative_path="domain/core/models.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="direct domain implementation module is flagged",
            rule_code="SFR307",
            relative_path="domain/service.py",
            source="value: int = 1\n",
            expected_codes=("SFR307",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="domain init module is allowed",
            rule_code="SFR307",
            relative_path="domain/__init__.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_layouts_when_checking_then_flags_only_layout_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="entry module without public function is flagged",
            rule_code="SFR401",
            relative_path="domain/core/main/run.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("SFR401",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="entry module with one public and two private functions is allowed",
            rule_code="SFR401",
            relative_path="domain/core/main/run.py",
            source=(
                "def run() -> None:\n    return None\n\n"
                "def _prepare() -> None:\n    return None\n\n"
                "def _finish() -> None:\n    return None\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="entry module runtime assignment is flagged",
            rule_code="SFR401",
            relative_path="domain/core/main/run.py",
            source="VALUE: int = 1\n\ndef run() -> None:\n    return None\n",
            expected_codes=("SFR401",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="nested nonempty init is flagged",
            rule_code="SFR402",
            relative_path="domain/core/__init__.py",
            source="value: int = 1\n",
            expected_codes=("SFR402",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="root package init is allowed as public surface",
            rule_code="SFR402",
            relative_path="__init__.py",
            source="from pkg.domain import value\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="root public surface allows imports and one all declaration",
            rule_code="SFR406",
            relative_path="__init__.py",
            source=(
                '"""Public package surface."""\n\n'
                "from pkg.domain.models import Model\n\n"
                "__all__ = ['Model']\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="root public surface function is flagged",
            rule_code="SFR406",
            relative_path="__init__.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("SFR406",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="root public surface runtime assignment is flagged",
            rule_code="SFR406",
            relative_path="__init__.py",
            source="VERSION: str = '1'\n",
            expected_codes=("SFR406",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="root public surface duplicate all declaration is flagged",
            rule_code="SFR406",
            relative_path="__init__.py",
            source="__all__ = ['First']\n__all__ = ['Second']\n",
            expected_codes=("SFR406",),
            expected_lines=(2,),
        ),
        SfrRuleTestCase(
            description="nested init is outside public surface shape rule",
            rule_code="SFR406",
            relative_path="domain/__init__.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="internal pure reexport module is flagged",
            rule_code="SFR403",
            relative_path="domain/core/service.py",
            source="from pkg.domain.core.impl import value\n\n__all__ = ['value']\n",
            expected_codes=("SFR403",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="module with implementation is not a reexport shim",
            rule_code="SFR403",
            relative_path="domain/core/service.py",
            source="from pkg.domain.core.impl import value\n\ndef run() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="helper all export is flagged",
            rule_code="SFR404",
            relative_path="domain/core/helpers/values.py",
            source="__all__ = ['value']\n\nvalue: int = 1\n",
            expected_codes=("SFR404",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="all export outside helpers is unaffected",
            rule_code="SFR404",
            relative_path="domain/core/service.py",
            source="__all__ = ['value']\n\nvalue: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="flat main entry colliding with package is flagged",
            rule_code="SFR405",
            relative_path="domain/core/main/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                SfrSupportFile(
                    description="colliding package",
                    relative_path="domain/core/main/run/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("SFR405",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="flat main entry without package is allowed",
            rule_code="SFR405",
            relative_path="domain/core/main/run.py",
            source="def run() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_surfaces_when_checking_then_flags_only_surface_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="classes module with two classes is flagged",
            rule_code="SFR501",
            relative_path="domain/core/classes/service.py",
            source="class First:\n    pass\n\nclass Second:\n    pass\n",
            expected_codes=("SFR501",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="classes module with one class is allowed",
            rule_code="SFR501",
            relative_path="domain/core/classes/service.py",
            source="class Service:\n    pass\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="main module under helpers is flagged",
            rule_code="SFR502",
            relative_path="domain/core/helpers/main.py",
            source="def run() -> None:\n    return None\n",
            expected_codes=("SFR502",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="shallow helper concern module is allowed",
            rule_code="SFR502",
            relative_path="domain/core/helpers/parsing/values.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="deep helper concern module is flagged",
            rule_code="SFR502",
            relative_path="domain/core/helpers/parsing/text/values.py",
            source="value: int = 1\n",
            expected_codes=("SFR502",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="private constant after function is flagged",
            rule_code="SFR503",
            relative_path="domain/core/helpers/values.py",
            source="def run() -> None:\n    return None\n\n_VALUE: int = 1\n",
            expected_codes=("SFR503",),
            expected_lines=(4,),
        ),
        SfrRuleTestCase(
            description="private constant before function is allowed",
            rule_code="SFR503",
            relative_path="domain/core/helpers/values.py",
            source="_VALUE: int = 1\n\ndef run() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="source above configured line limit is flagged",
            rule_code="SFR601",
            relative_path="domain/core/helpers/values.py",
            source="first: int = 1\nsecond: int = 2\nthird: int = 3\n",
            thresholds={Threshold.MAX_FILE_LINES: 2},
            expected_codes=("SFR601",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="source at configured line limit is allowed",
            rule_code="SFR601",
            relative_path="domain/core/helpers/values.py",
            source="first: int = 1\nsecond: int = 2\n",
            thresholds={Threshold.MAX_FILE_LINES: 2},
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_module_shapes_when_checking_then_flags_only_shape_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
