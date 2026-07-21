"""Tests for roles rules."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from fensu.analysis.types import ProjectDependencyKind
from fensu.config.models import ThresholdOverride
from fensu.discovery.types import ScopeName
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Threshold
from tests.unit.src.fensu.rules.roles.main import helpers as role_test_helpers
from tests.unit.src.fensu.rules.roles.main._test_types import (
    ContainerScaleTestCase,
    FfrRuleTestCase,
    FfrSupportFile,
)
from tests.unit.src.fensu.rules.roles.main.helpers import (
    evaluate_flat_helpers_scale,
    evaluate_role_test_case,
)

_LOCAL_NATIVE_SFR_CODES: frozenset[str] = frozenset(
    {
        "FFR001",
        "FFR002",
        "FFR003",
        "FFR004",
        "FFR101",
        "FFR102",
        "FFR103",
        "FFR104",
        "FFR201",
        "FFR202",
        "FFR203",
        "FFR204",
        "FFR205",
        "FFR301",
        "FFR302",
        "FFR303",
        "FFR304",
        "FFR305",
        "FFR306",
        "FFR307",
        "FFR308",
        "FFR309",
        "FFR401",
        "FFR402",
        "FFR403",
        "FFR404",
        "FFR405",
        "FFR406",
        "FFR501",
        "FFR502",
        "FFR503",
        "FFR601",
        "FFR701",
        "FFR702",
        "FFR703",
        "FFR704",
        "FFR705",
        "FFR706",
        "FFR707",
    }
)


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="runtime function in models role is flagged",
            rule_code="FFR001",
            relative_path="domain/core/models.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("FFR001",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="dataclass in models role is allowed",
            rule_code="FFR001",
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
        FfrRuleTestCase(
            description="runtime function in types role is flagged",
            rule_code="FFR002",
            relative_path="domain/core/types.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("FFR002",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="protocol in types role is allowed",
            rule_code="FFR002",
            relative_path="domain/core/types.py",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="private dataclass protocol in types role is flagged as a model",
            rule_code="FFR002",
            relative_path="domain/core/types.py",
            source=(
                "from dataclasses import dataclass\n"
                "from typing import Protocol\n\n"
                "@dataclass\n"
                "class _Event(Protocol):\n"
                "    value: int\n"
            ),
            expected_codes=("FFR002",),
            expected_lines=(5,),
        ),
        FfrRuleTestCase(
            description="type-checking imports-only block in types role is allowed",
            rule_code="FFR002",
            relative_path="domain/core/types.py",
            source="if TYPE_CHECKING:\n    from domain.core.models import Result\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="non-import in type-checking block in types role is flagged",
            rule_code="FFR002",
            relative_path="domain/core/types.py",
            source="if TYPE_CHECKING:\n    value: int = 1\n",
            expected_codes=("FFR002",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="type-checking block with else in types role is flagged",
            rule_code="FFR002",
            relative_path="domain/core/types.py",
            source="if TYPE_CHECKING:\n    from domain.core.models import Result\nelse:\n    Result = object\n",
            expected_codes=("FFR002",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="class in constants role is flagged",
            rule_code="FFR003",
            relative_path="domain/core/constants.py",
            source="class Config:\n    value: int\n",
            expected_codes=("FFR003",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="assignment in constants role is allowed",
            rule_code="FFR003",
            relative_path="domain/core/constants.py",
            source="DEFAULT_VALUE: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="plain class in exceptions role is flagged",
            rule_code="FFR004",
            relative_path="domain/core/exceptions.py",
            source="class Result:\n    value: int\n",
            expected_codes=("FFR004",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="custom error in exceptions role is allowed",
            rule_code="FFR004",
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
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="unanchored outer generic package does not hide anchored nested package",
            rule_code="FFR204",
            relative_path="shared/zeta/misc/value.py",
            source="value: int = 1\n",
            support_files=(
                FfrSupportFile(
                    description="outer shared package anchor",
                    relative_path="shared/alpha/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR204", "FFR204"),
            expected_lines=(None, None),
            expected_messages=(
                "shared/ does not identify an owner; name the business or technical capability",
                "misc/ does not identify an owner; name the business or technical capability",
            ),
            expected_paths=("shared/alpha/models.py", "shared/zeta/misc/value.py"),
        ),
        FfrRuleTestCase(
            description="one anchor reports every nested generic package",
            rule_code="FFR204",
            relative_path="domain/util/utils/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204", "FFR204"),
            expected_lines=(None, None),
            expected_messages=(
                "util/ does not identify an owner; name the business or technical capability",
                "utils/ does not identify an owner; name the business or technical capability",
            ),
            expected_paths=("domain/util/utils/value.py", "domain/util/utils/value.py"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_nested_generic_packages_when_checking_then_reports_each_anchored_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )
    scope_root: Path = tmp_path / "src/pkg"

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert tuple(fault.path.relative_to(scope_root).as_posix() for fault in result.faults) == (
        test_case.expected_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="dataclass outside models role is flagged",
            rule_code="FFR101",
            relative_path="domain/core/_helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Result:\n"
                "    value: int\n"
            ),
            expected_codes=("FFR101",),
            expected_lines=(4,),
        ),
        FfrRuleTestCase(
            description="private dataclass outside models role is allowed",
            rule_code="FFR101",
            relative_path="domain/core/_helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class _Result:\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="protocol outside types role is flagged",
            rule_code="FFR102",
            relative_path="domain/core/classes/service.py",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_codes=("FFR102",),
            expected_lines=(3,),
        ),
        FfrRuleTestCase(
            description="private protocol in helpers role is allowed",
            rule_code="FFR102",
            relative_path="domain/core/_helpers/service.py",
            source="from typing import Protocol\n\nclass _Service(Protocol):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="private dataclass protocol outside types is not a type declaration",
            rule_code="FFR102",
            relative_path="domain/core/classes/event.py",
            source=(
                "from dataclasses import dataclass\n"
                "from typing import Protocol\n\n"
                "@dataclass\n"
                "class _Event(Protocol):\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="explicit TypeAlias outside types role is flagged",
            rule_code="FFR102",
            relative_path="domain/core/_helpers/aliases.py",
            source=(
                "from typing import Literal, TypeAlias\n\n"
                "PathMode: TypeAlias = Literal['short', 'full']\n"
            ),
            expected_codes=("FFR102",),
            expected_lines=(3,),
        ),
        FfrRuleTestCase(
            description="public uppercase constant outside constants role is flagged",
            rule_code="FFR103",
            relative_path="domain/core/_helpers/values.py",
            source="DEFAULT_VALUE: int = 1\n",
            expected_codes=("FFR103",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="private uppercase constant outside constants role is allowed",
            rule_code="FFR103",
            relative_path="domain/core/_helpers/values.py",
            source="_DEFAULT_VALUE: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="custom error outside exceptions role is flagged",
            rule_code="FFR104",
            relative_path="domain/core/_helpers/errors.py",
            source="class ConfigError(Exception):\n    pass\n",
            expected_codes=("FFR104",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="plain class outside exceptions role is allowed",
            rule_code="FFR104",
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
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="misc filename is flagged",
            rule_code="FFR201",
            relative_path="domain/core/_helpers/misc.py",
            source="value: int = 1\n",
            expected_codes=("FFR201",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="common filename inside an owned role is allowed",
            rule_code="FFR201",
            relative_path="domain/core/_helpers/common.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="shared domain package is flagged",
            rule_code="FFR204",
            relative_path="shared/core/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="legacy helpers package is rejected instead of treated as a role",
            rule_code="FFR204",
            relative_path="domain/core/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="shared subdomain package is flagged",
            rule_code="FFR204",
            relative_path="domain/shared/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="shared package deeper than subdomain is flagged",
            rule_code="FFR204",
            relative_path="domain/orders/_helpers/shared/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="common domain package is flagged",
            rule_code="FFR204",
            relative_path="common/core/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="util domain package is flagged",
            rule_code="FFR204",
            relative_path="util/core/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="utils subdomain package is flagged",
            rule_code="FFR204",
            relative_path="domain/utils/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="misc subdomain package is flagged",
            rule_code="FFR204",
            relative_path="domain/misc/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="base subdomain package is flagged",
            rule_code="FFR204",
            relative_path="domain/base/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="lib subdomain package is flagged",
            rule_code="FFR204",
            relative_path="domain/lib/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="generic package name inside helpers role is flagged",
            rule_code="FFR204",
            relative_path="domain/core/_helpers/utils/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="deeper misc package is flagged",
            rule_code="FFR204",
            relative_path="domain/orders/_helpers/parsing/misc/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="deeper util package is flagged",
            rule_code="FFR204",
            relative_path="domain/orders/_helpers/parsing/util/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR204",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="generic module filename is not treated as a package",
            rule_code="FFR204",
            relative_path="domain/orders/_helpers/misc.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="tooling generic package names remain outside runtime package rule",
            rule_code="FFR204",
            relative_path="shared/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="domain-specific package names are allowed",
            rule_code="FFR204",
            relative_path="orders/compile/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="helpers module filename is flagged",
            rule_code="FFR202",
            relative_path="domain/core/helpers.py",
            source="value: int = 1\n",
            expected_codes=("FFR202",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="classes module filename is flagged",
            rule_code="FFR203",
            relative_path="domain/core/classes.py",
            source="class Service:\n    value: int\n",
            expected_codes=("FFR203",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="public plain class in helpers is flagged",
            rule_code="FFR205",
            relative_path="domain/core/_helpers/service.py",
            source="class Service:\n    value: int\n",
            expected_codes=("FFR205",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="private plain class in helpers is allowed",
            rule_code="FFR205",
            relative_path="domain/core/_helpers/service.py",
            source="class _Service:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="plain class in classes role is unaffected",
            rule_code="FFR205",
            relative_path="domain/core/classes/service.py",
            source="class Service:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="public dataclass in helpers is left to model ownership rule",
            rule_code="FFR205",
            relative_path="domain/core/_helpers/results.py",
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
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="helpers package mixing modules and subfolders is flagged",
            rule_code="FFR301",
            relative_path="domain/core/_helpers/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="flat helper",
                    relative_path="domain/core/_helpers/values.py",
                    source="value: int = 1\n",
                ),
                FfrSupportFile(
                    description="helper concern",
                    relative_path="domain/core/_helpers/parsing/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR301",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="helpers package over flat threshold is flagged",
            rule_code="FFR301",
            relative_path="domain/core/_helpers/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="first helper",
                    relative_path="domain/core/_helpers/first.py",
                    source="value: int = 1\n",
                ),
                FfrSupportFile(
                    description="second helper",
                    relative_path="domain/core/_helpers/second.py",
                    source="value: int = 2\n",
                ),
            ),
            thresholds={Threshold.MAX_HELPERS_CONTAINER_MODULES: 1},
            expected_codes=("FFR301",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="flat helpers package under threshold is allowed",
            rule_code="FFR301",
            relative_path="domain/core/_helpers/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="flat helper",
                    relative_path="domain/core/_helpers/values.py",
                    source="value: int = 1\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="main role-named bucket is flagged",
            rule_code="FFR302",
            relative_path="domain/core/main/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR302",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="nested direct support module is flagged",
            rule_code="FFR304",
            relative_path="domain/core/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR304",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="nested role module is allowed",
            rule_code="FFR304",
            relative_path="domain/core/models.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="arbitrary nested direct subpackage is flagged",
            rule_code="FFR305",
            relative_path="domain/core/feature/__init__.py",
            source="",
            expected_codes=("FFR305",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="nested direct subpackage without init is flagged",
            rule_code="FFR305",
            relative_path="domain/core/feature/implementation.py",
            source="value: int = 1\n",
            expected_codes=("FFR305",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="nested helpers subpackage is allowed",
            rule_code="FFR305",
            relative_path="domain/core/_helpers/parsing.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="shared package has no nested structural exception",
            rule_code="FFR305",
            relative_path="domain/core/shared/value.py",
            source="value: int = 1\n",
            expected_codes=("FFR305",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="leaf ignores direct asset data and empty directories",
            rule_code="FFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="direct main role content",
                    relative_path="domain/main/run.py",
                    source="def run() -> None:\n    return None\n",
                ),
                FfrSupportFile(
                    description="asset directory without Python",
                    relative_path="domain/assets/logo.svg",
                    source="<svg/>\n",
                ),
                FfrSupportFile(
                    description="data directory without Python",
                    relative_path="domain/data/records.json",
                    source="[]\n",
                ),
                FfrSupportFile(
                    description="empty directory",
                    relative_path="domain/empty",
                    source="",
                    is_directory=True,
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="asset directory becomes a named subdomain when Python source appears",
            rule_code="FFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="asset namespace Python source",
                    relative_path="domain/assets/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR306",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="top-level domain with named subdomains is a legal branch",
            rule_code="FFR306",
            relative_path="domain/orders/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="second named subdomain",
                    relative_path="domain/customers/main/read.py",
                    source="def read() -> None:\n    return None\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="top-level domain mixing direct main role and named subdomain is flagged",
            rule_code="FFR306",
            relative_path="domain/main/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                FfrSupportFile(
                    description="named subdomain role file",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR306",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="top-level domain mixing direct role file and named subdomain is flagged",
            rule_code="FFR306",
            relative_path="domain/types.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="named subdomain role file",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR306",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="shared top-level domain follows mixed domain semantics",
            rule_code="FFR306",
            relative_path="shared/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="named subdomain below shared domain",
                    relative_path="shared/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR306",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="shared direct child is a named subdomain for domain shape",
            rule_code="FFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="banned shared subdomain",
                    relative_path="domain/shared/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR306",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="role file below subpackage remains allowed",
            rule_code="FFR306",
            relative_path="domain/core/models.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="direct domain implementation module is flagged",
            rule_code="FFR307",
            relative_path="domain/service.py",
            source="value: int = 1\n",
            expected_codes=("FFR307",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="domain init module is allowed",
            rule_code="FFR307",
            relative_path="domain/__init__.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="direct domain role module does not require a subdomain",
            rule_code="FFR307",
            relative_path="domain/main.py",
            source="def main() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="annotation sibling domains require one parent domain",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="annotation export domain",
                    relative_path="annotation_export/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="annotation sanitization domain",
                    relative_path="annotation_sanitization/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="annotation validation domain",
                    relative_path="annotation_validation/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR308",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="first token groups broad salesforce ownership",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="salesforce annotation export domain",
                    relative_path="salesforce_annotation_export/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="salesforce annotation validation domain",
                    relative_path="salesforce_annotation_validation/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="salesforce events domain",
                    relative_path="salesforce_events/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR308",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="configured minimum suppresses a smaller shared-prefix group",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="first salesforce domain",
                    relative_path="salesforce_api/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="second salesforce domain",
                    relative_path="salesforce_events/__init__.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MIN_SHARED_DOMAIN_PREFIX_PACKAGES: 3},
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="zero minimum disables shared-prefix detection",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="first salesforce domain",
                    relative_path="salesforce_api/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="second salesforce domain",
                    relative_path="salesforce_events/__init__.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MIN_SHARED_DOMAIN_PREFIX_PACKAGES: 0},
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="arbitrary character prefixes do not group domains",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="annotate domain",
                    relative_path="annotate_export/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="annotation domain",
                    relative_path="annotation_validation/__init__.py",
                    source="",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="non-Python sibling directory does not count toward the minimum",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="Python annotation domain",
                    relative_path="annotation_export/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="asset-only annotation directory",
                    relative_path="annotation_assets/logo.svg",
                    source="<svg/>\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="organized parent domain does not inspect nested subdomain prefixes",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="annotation export subdomain",
                    relative_path="annotation/export/models.py",
                    source="",
                ),
                FfrSupportFile(
                    description="annotation validation subdomain",
                    relative_path="annotation/validation/models.py",
                    source="",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="multiple owner prefixes emit one deterministic fault each",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="annotation export domain",
                    relative_path="annotation_export/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="annotation validation domain",
                    relative_path="annotation_validation/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="billing export domain",
                    relative_path="billing_export/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="billing validation domain",
                    relative_path="billing_validation/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR308", "FFR308"),
            expected_lines=(None, None),
        ),
        FfrRuleTestCase(
            description="tooling packages do not participate in runtime domain grouping",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="first tooling package",
                    relative_path="salesforce_api/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="second tooling package",
                    relative_path="salesforce_events/__init__.py",
                    source="",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_layouts_when_checking_then_flags_only_layout_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="broad owner prefix reports exact parent and subdomain guidance",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="salesforce annotation export domain",
                    relative_path="salesforce_annotation_export/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="salesforce annotation validation domain",
                    relative_path="salesforce_annotation_validation/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="salesforce events domain",
                    relative_path="salesforce_events/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR308",),
            expected_lines=(None,),
            expected_messages=(
                "sibling domains salesforce_annotation_export, "
                "salesforce_annotation_validation, and salesforce_events share the "
                "salesforce_ owner prefix",
            ),
            expected_remediations=(
                "Create salesforce/ and move them beneath it as annotation_export/, "
                "annotation_validation/, and events/ subdomains.",
            ),
            expected_paths=("src/pkg/__init__.py",),
        ),
        FfrRuleTestCase(
            description="existing parent domain receives prefixed siblings",
            rule_code="FFR308",
            relative_path="__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="existing salesforce domain",
                    relative_path="salesforce/models.py",
                    source="",
                ),
                FfrSupportFile(
                    description="salesforce annotation domain",
                    relative_path="salesforce_annotation/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="salesforce events domain",
                    relative_path="salesforce_events/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR308",),
            expected_lines=(None,),
            expected_messages=(
                "sibling domains salesforce_annotation and salesforce_events share the "
                "salesforce_ owner prefix",
            ),
            expected_remediations=(
                "Move them under the existing salesforce/ domain as annotation/ and events/ "
                "subdomains.",
            ),
            expected_paths=("src/pkg/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_shared_domain_prefix_when_reporting_then_names_broad_parent_and_subdomains(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert tuple(fault.remediation for fault in result.faults) == test_case.expected_remediations
    assert (
        tuple(fault.path.relative_to(tmp_path).as_posix() for fault in result.faults)
        == test_case.expected_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="helpers bucket module cap reports observed and effective values",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="bucket init",
                    relative_path="domain/orders/_helpers/parsing/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="first module",
                    relative_path="domain/orders/_helpers/parsing/first.py",
                    source="",
                ),
                FfrSupportFile(
                    description="second module",
                    relative_path="domain/orders/_helpers/parsing/second.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_HELPERS_CONTAINER_MODULES: 1},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ container has 2 modules; effective limit is 1",),
            expected_paths=("domain/orders/_helpers/parsing/__init__.py",),
        ),
        FfrRuleTestCase(
            description="matching override raises bucket module cap at reported anchor",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="bucket init",
                    relative_path="domain/orders/_helpers/parsing/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="first module",
                    relative_path="domain/orders/_helpers/parsing/first.py",
                    source="",
                ),
                FfrSupportFile(
                    description="second module",
                    relative_path="domain/orders/_helpers/parsing/second.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_HELPERS_CONTAINER_MODULES: 1},
            threshold_overrides=(
                ThresholdOverride(
                    paths=("src/pkg/**/_helpers/parsing/__init__.py",),
                    thresholds={Threshold.MAX_HELPERS_CONTAINER_MODULES: 2},
                    reason="Parser breadth.",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            expected_messages=(),
            expected_paths=(),
        ),
        FfrRuleTestCase(
            description="namespace helpers root anchors one deep bucket fault",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/parsing/text/read.py",
            source="def read() -> None:\n    return None\n",
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket depth is 2; effective limit is 1",),
            expected_paths=("domain/orders/_helpers/parsing/text/read.py",),
        ),
        FfrRuleTestCase(
            description="main grouped bucket enforces its own module cap",
            rule_code="FFR302",
            relative_path="domain/orders/main/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="bucket init",
                    relative_path="domain/orders/main/commands/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="first command",
                    relative_path="domain/orders/main/commands/first.py",
                    source="",
                ),
                FfrSupportFile(
                    description="second command",
                    relative_path="domain/orders/main/commands/second.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_MAIN_CONTAINER_MODULES: 1},
            expected_codes=("FFR302",),
            expected_lines=(None,),
            expected_messages=("main/ container has 2 modules; effective limit is 1",),
            expected_paths=("domain/orders/main/commands/__init__.py",),
        ),
        FfrRuleTestCase(
            description="role-named bucket is faulted once from the outer helpers root",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/read.py",
            source="def read() -> None:\n    return None\n",
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/read.py",),
        ),
        FfrRuleTestCase(
            description="nested main bucket is faulted once with raised depth",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="nested helpers bucket is faulted once with raised depth",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/_helpers/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket '_helpers/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/_helpers/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="nested classes bucket is faulted once with raised depth",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/classes/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'classes/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/classes/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="nested models bucket is faulted once with raised depth",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/models/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'models/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/models/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="nested types bucket is faulted once with raised depth",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/types/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'types/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/types/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="nested constants bucket is faulted once with raised depth",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/constants/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'constants/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/constants/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="nested exceptions bucket is faulted once with raised depth",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/exceptions/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'exceptions/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/exceptions/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="nested role bucket is also detected below main",
            rule_code="FFR302",
            relative_path="domain/orders/main/classes/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR302",),
            expected_lines=(None,),
            expected_messages=("main/ bucket 'classes/' uses a runtime role name",),
            expected_paths=("domain/orders/main/classes/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="ancestor role bucket initializer owns fault instead of descendant anchor",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            support_files=(
                FfrSupportFile(
                    description="forbidden bucket initializer",
                    relative_path="domain/orders/_helpers/main/__init__.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/__init__.py",),
        ),
        FfrRuleTestCase(
            description="direct Python file owns role bucket fault before descendants",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            support_files=(
                FfrSupportFile(
                    description="direct bucket module",
                    relative_path="domain/orders/_helpers/main/owner.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301", "FFR301"),
            expected_lines=(None, None),
            expected_messages=(
                "_helpers/ container mixes direct modules and Python buckets",
                "_helpers/ bucket 'main/' uses a runtime role name",
            ),
            expected_paths=(
                "domain/orders/_helpers/main/owner.py",
                "domain/orders/_helpers/main/owner.py",
            ),
        ),
        FfrRuleTestCase(
            description="lexicographically first direct Python file owns role bucket fault",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/zulu.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="lexically first direct module",
                    relative_path="domain/orders/_helpers/main/alpha.py",
                    source="",
                ),
            ),
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/alpha.py",),
        ),
        FfrRuleTestCase(
            description="lexicographically first descendant owns namespace role bucket fault",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/zulu/read.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="lexically first descendant module",
                    relative_path="domain/orders/_helpers/main/alpha/read.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/alpha/read.py",),
        ),
        FfrRuleTestCase(
            description="multiple invalid segments each emit one bucket-owned fault",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/classes/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR301", "FFR301"),
            expected_lines=(None, None),
            expected_messages=(
                "_helpers/ bucket 'main/' uses a runtime role name",
                "_helpers/ bucket 'classes/' uses a runtime role name",
            ),
            expected_paths=(
                "domain/orders/_helpers/main/classes/read.py",
                "domain/orders/_helpers/main/classes/read.py",
            ),
        ),
        FfrRuleTestCase(
            description="nested generic shared bucket remains only FFR204 ownership",
            rule_code="FFR",
            relative_path="domain/orders/_helpers/shared/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            support_files=(
                FfrSupportFile(
                    description="meaningful leaf main entry",
                    relative_path="domain/orders/main/run.py",
                    source="def run() -> None:\n    return None\n",
                ),
            ),
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("FFR204",),
            expected_lines=(None,),
            expected_messages=(
                "shared/ does not identify an owner; name the business or technical capability",
            ),
            expected_paths=("domain/orders/_helpers/shared/parsing/read.py",),
        ),
        FfrRuleTestCase(
            description="namespace helpers root detects init-only role-named bucket",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/main/__init__.py",
            source="",
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/__init__.py",),
        ),
        FfrRuleTestCase(
            description="generic and asset buckets do not create FFR301 faults",
            rule_code="FFR301",
            relative_path="domain/orders/_helpers/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="generic bucket",
                    relative_path="domain/orders/_helpers/misc/read.py",
                    source="",
                ),
                FfrSupportFile(
                    description="asset",
                    relative_path="domain/orders/_helpers/assets/logo.svg",
                    source="<svg/>",
                ),
                FfrSupportFile(
                    description="empty directory",
                    relative_path="domain/orders/_helpers/empty",
                    source="",
                    is_directory=True,
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            expected_messages=(),
            expected_paths=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_containers_when_checking_layout_then_enforces_shared_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert (
        tuple(fault.path.relative_to(tmp_path / "src/pkg").as_posix() for fault in result.faults)
        == test_case.expected_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ContainerScaleTestCase(
            description="tenfold flat role width keeps aggregate project queries near linear",
            small_module_count=10,
            large_module_count=100,
            expected_max_query_multiplier=11,
            expected_small_fault_count=0,
            expected_large_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_wider_role_when_evaluating_containers_then_project_queries_grow_near_linearly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ContainerScaleTestCase,
) -> None:
    small: EvaluationResult = evaluate_flat_helpers_scale(
        project_root=tmp_path / "small",
        module_count=test_case.small_module_count,
        monkeypatch=monkeypatch,
    )
    large: EvaluationResult = evaluate_flat_helpers_scale(
        project_root=tmp_path / "large",
        module_count=test_case.large_module_count,
        monkeypatch=monkeypatch,
    )
    observed_kinds: frozenset[ProjectDependencyKind] = frozenset(
        {
            ProjectDependencyKind.DIRECTORY_ENTRIES,
            ProjectDependencyKind.GLOB,
            ProjectDependencyKind.IS_FILE,
        }
    )
    small_query_count: int = sum(
        dependency.kind in observed_kinds for dependency in small.dependencies
    )
    large_query_count: int = sum(
        dependency.kind in observed_kinds for dependency in large.dependencies
    )

    assert len(small.faults) == test_case.expected_small_fault_count
    assert len(large.faults) == test_case.expected_large_fault_count
    assert large_query_count <= small_query_count * test_case.expected_max_query_multiplier


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="helpers main bucket has no secondary entry or main-shape faults",
            rule_code="FF",
            relative_path="domain/orders/_helpers/main/read.py",
            source="def _prepare() -> None:\n    value: int = build()\n",
            support_files=(
                FfrSupportFile(
                    description="meaningful leaf main entry",
                    relative_path="domain/orders/main/_run.py",
                    source="def run() -> None:\n    return None\n",
                ),
            ),
            thresholds={
                Threshold.MAX_STATEMENTS: 0,
                Threshold.MAX_DISTINCT_CALLS: 0,
                Threshold.MAX_LOCALS: 0,
            },
            threshold_overrides=(
                ThresholdOverride(
                    paths=("src/pkg/domain/orders/main/_run.py",),
                    thresholds={
                        Threshold.MAX_STATEMENTS: 1,
                        Threshold.MAX_DISTINCT_CALLS: 1,
                        Threshold.MAX_LOCALS: 1,
                    },
                    reason="Keep the support entry valid while probing helper ownership.",
                ),
            ),
            expected_codes=("FFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/read.py",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_role_named_bucket_when_running_full_rules_then_avoids_main_double_faults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert (
        tuple(fault.path.relative_to(tmp_path / "src/pkg").as_posix() for fault in result.faults)
        == test_case.expected_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="mixed domain anchors one fault at its init module",
            rule_code="FFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="domain init anchor",
                    relative_path="domain/__init__.py",
                    source="",
                ),
                FfrSupportFile(
                    description="named subdomain",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR306",),
            expected_lines=(None,),
            expected_paths=("domain/__init__.py",),
        ),
        FfrRuleTestCase(
            description="mixed domain without init anchors one fault at first Python file",
            rule_code="FFR306",
            relative_path="domain/types.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="lexically first named subdomain file",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR306",),
            expected_lines=(None,),
            expected_paths=("domain/orders/models.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_top_level_domain_when_checking_then_anchors_one_deterministic_fault(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )
    scope_root: Path = tmp_path / "src/pkg"

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.path.relative_to(scope_root).as_posix() for fault in result.faults) == (
        test_case.expected_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="entry module without public function is flagged",
            rule_code="FFR401",
            relative_path="domain/core/main/run.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("FFR401",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="entry module with one public and two private functions is allowed",
            rule_code="FFR401",
            relative_path="domain/core/main/run.py",
            source=(
                "def run() -> None:\n    return None\n\n"
                "def _prepare() -> None:\n    return None\n\n"
                "def _finish() -> None:\n    return None\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="entry module runtime assignment is flagged",
            rule_code="FFR401",
            relative_path="domain/core/main/run.py",
            source="VALUE: int = 1\n\ndef run() -> None:\n    return None\n",
            expected_codes=("FFR401",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="grouped main module is checked as an entry",
            rule_code="FFR401",
            relative_path="domain/core/main/commands/run.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("FFR401",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="main.py under main is checked as an entry",
            rule_code="FFR401",
            relative_path="domain/core/main/main.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("FFR401",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="nested nonempty init is flagged",
            rule_code="FFR402",
            relative_path="domain/core/__init__.py",
            source="value: int = 1\n",
            expected_codes=("FFR402",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="root package init is allowed as public surface",
            rule_code="FFR402",
            relative_path="__init__.py",
            source="from pkg.domain import value\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="root public surface allows imports and one all declaration",
            rule_code="FFR406",
            relative_path="__init__.py",
            source=(
                '"""Public package surface."""\n\n'
                "from pkg.domain.models import Model\n\n"
                "__all__ = ['Model']\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="root public surface function is flagged",
            rule_code="FFR406",
            relative_path="__init__.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("FFR406",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="root public surface runtime assignment is flagged",
            rule_code="FFR406",
            relative_path="__init__.py",
            source="VERSION: str = '1'\n",
            expected_codes=("FFR406",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="root public surface duplicate all declaration is flagged",
            rule_code="FFR406",
            relative_path="__init__.py",
            source="__all__ = ['First']\n__all__ = ['Second']\n",
            expected_codes=("FFR406",),
            expected_lines=(2,),
        ),
        FfrRuleTestCase(
            description="nested init is outside public surface shape rule",
            rule_code="FFR406",
            relative_path="domain/__init__.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="internal pure reexport module is flagged",
            rule_code="FFR403",
            relative_path="domain/core/service.py",
            source="from pkg.domain.core.impl import value\n\n__all__ = ['value']\n",
            expected_codes=("FFR403",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="module with implementation is not a reexport shim",
            rule_code="FFR403",
            relative_path="domain/core/service.py",
            source="from pkg.domain.core.impl import value\n\ndef run() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="helper all export is flagged",
            rule_code="FFR404",
            relative_path="domain/core/_helpers/values.py",
            source="__all__ = ['value']\n\nvalue: int = 1\n",
            expected_codes=("FFR404",),
            expected_lines=(1,),
        ),
        FfrRuleTestCase(
            description="all export outside helpers is unaffected",
            rule_code="FFR404",
            relative_path="domain/core/service.py",
            source="__all__ = ['value']\n\nvalue: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="flat main entry colliding with package is flagged",
            rule_code="FFR405",
            relative_path="domain/core/main/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                FfrSupportFile(
                    description="colliding package",
                    relative_path="domain/core/main/run/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR405",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="flat main entry without package is allowed",
            rule_code="FFR405",
            relative_path="domain/core/main/run.py",
            source="def run() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="grouped main entry colliding with package is flagged",
            rule_code="FFR405",
            relative_path="domain/core/main/commands/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                FfrSupportFile(
                    description="grouped colliding package",
                    relative_path="domain/core/main/commands/run/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR405",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="flat main entry sharing its name with a file is allowed",
            rule_code="FFR405",
            relative_path="domain/core/main/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                FfrSupportFile(
                    description="same-named plain file",
                    relative_path="domain/core/main/run",
                    source="",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_surfaces_when_checking_then_flags_only_surface_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="classes module with two classes is flagged",
            rule_code="FFR501",
            relative_path="domain/core/classes/service.py",
            source="class First:\n    pass\n\nclass Second:\n    pass\n",
            expected_codes=("FFR501",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="classes module with one class is allowed",
            rule_code="FFR501",
            relative_path="domain/core/classes/service.py",
            source="class Service:\n    pass\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="main module under helpers is flagged",
            rule_code="FFR502",
            relative_path="domain/core/_helpers/main.py",
            source="def run() -> None:\n    return None\n",
            expected_codes=("FFR502",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="shallow helper concern module is allowed",
            rule_code="FFR502",
            relative_path="domain/core/_helpers/parsing/values.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="deep helper concern module depth belongs to FFR301",
            rule_code="FFR502",
            relative_path="domain/core/_helpers/parsing/text/values.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="private constant after function is flagged",
            rule_code="FFR503",
            relative_path="domain/core/_helpers/values.py",
            source="def run() -> None:\n    return None\n\n_VALUE: int = 1\n",
            expected_codes=("FFR503",),
            expected_lines=(4,),
        ),
        FfrRuleTestCase(
            description="private constant before function is allowed",
            rule_code="FFR503",
            relative_path="domain/core/_helpers/values.py",
            source="_VALUE: int = 1\n\ndef run() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="source above configured line limit is flagged",
            rule_code="FFR601",
            relative_path="domain/core/_helpers/values.py",
            source="first: int = 1\nsecond: int = 2\nthird: int = 3\n",
            thresholds={Threshold.MAX_FILE_LINES: 2},
            expected_codes=("FFR601",),
            expected_lines=(None,),
        ),
        FfrRuleTestCase(
            description="source at configured line limit is allowed",
            rule_code="FFR601",
            relative_path="domain/core/_helpers/values.py",
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
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="all native FFR rules bypass their Python core callbacks",
            rule_code="FFR",
            relative_path="domain/core/_helpers/values.py",
            source="",
            expected_codes=("FFR309",),
            expected_lines=(None,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_registered_native_role_rule_when_evaluating_then_skips_python_callback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    python_callback: Mock = Mock(side_effect=AssertionError("Python callback executed"))
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in role_test_helpers.FFR_RULES}
    monkeypatch.setattr(
        role_test_helpers,
        "FFR_RULES",
        tuple(
            replace(rules_by_code[code], check=python_callback)
            for code in sorted(_LOCAL_NATIVE_SFR_CODES)
        ),
    )

    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert python_callback.call_count == 0


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="path-level entry fault inherits actionable catalogue remediation",
            rule_code="FFR401",
            relative_path="domain/core/main/run.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("FFR401",),
            expected_lines=(None,),
            expected_messages=("entry modules need one public function",),
            expected_remediations=(
                "Keep only imports, one public entry function, and at most two small private "
                "glue functions; move phase logic to _helpers/.",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_path_level_role_fault_when_evaluating_then_inherits_actionable_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert tuple(fault.remediation for fault in result.faults) == test_case.expected_remediations


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="direct script with private parser and public main is allowed",
            rule_code="FFR701",
            relative_path="generate_report.py",
            source=(
                "import argparse\n\n"
                "def _parse_args() -> argparse.Namespace:\n"
                "    return argparse.ArgumentParser().parse_args()\n\n"
                "def main() -> int:\n"
                "    return 0\n\n"
                "if __name__ == '__main__':\n"
                "    raise SystemExit(main())\n"
            ),
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="public parse_args in direct script is flagged",
            rule_code="FFR701",
            relative_path="generate_report.py",
            source=(
                "def parse_args() -> object:\n"
                "    return object()\n\n"
                "def main() -> int:\n"
                "    return 0\n"
            ),
            expected_codes=("FFR701",),
            expected_lines=(1,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="class in direct script is flagged",
            rule_code="FFR701",
            relative_path="generate_report.py",
            source="class Fetcher:\n    pass\n\ndef main() -> int:\n    return 0\n",
            expected_codes=("FFR701",),
            expected_lines=(1,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="direct script calling imported tooling main entry is allowed",
            rule_code="FFR702",
            relative_path="generate_report.py",
            source=(
                "from scripts.reporting.main.fetch import run_fetch\n\n"
                "def main() -> int:\n"
                "    return run_fetch()\n"
            ),
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="direct script without main delegation is flagged",
            rule_code="FFR702",
            relative_path="generate_report.py",
            source="def main() -> int:\n    return 0\n",
            expected_codes=("FFR702",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="implementation call retained in direct script main is flagged",
            rule_code="FFR702",
            relative_path="generate_report.py",
            source=(
                "import json\n"
                "from scripts.reporting.main.fetch import run_fetch\n\n"
                "def main() -> int:\n"
                "    result: object = run_fetch()\n"
                "    print(json.dumps(result))\n"
                "    return 0\n"
            ),
            expected_codes=("FFR702", "FFR702"),
            expected_lines=(6, 6),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="direct script above configured line limit is flagged",
            rule_code="FFR703",
            relative_path="generate_report.py",
            source="def main() -> int:\n    value: int = 1\n    return value\n",
            thresholds={Threshold.MAX_SCRIPT_ENTRYPOINT_LINES: 2},
            expected_codes=("FFR703",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="rules role allows multiple decorated functions",
            rule_code="FFR704",
            relative_path="fensu/rules/imports.py",
            source=(
                "from fensu import Family, rule\n\n"
                "@rule(code='XIM001', family=Family.CUSTOM, slug='first', message='first')\n"
                "def first(*, module: object, ctx: object) -> list[object]:\n"
                "    return []\n\n"
                "@rule(code='XIM002', family=Family.CUSTOM, slug='second', message='second')\n"
                "def second(*, module: object, ctx: object) -> list[object]:\n"
                "    return []\n"
            ),
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="undecorated function in rules role is flagged",
            rule_code="FFR704",
            relative_path="fensu/rules/imports.py",
            source="def helper() -> None:\n    return None\n",
            expected_codes=("FFR704",),
            expected_lines=(1,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="standard role directory directly under tool package is allowed",
            rule_code="FFR705",
            relative_path="reporting/main/fetch.py",
            source="def run_fetch() -> int:\n    return 0\n",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="arbitrary package directly under tool package is flagged",
            rule_code="FFR705",
            relative_path="reporting/work/fetch.py",
            source="def run_fetch() -> int:\n    return 0\n",
            expected_codes=("FFR705",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="direct implementation module under tool package is flagged",
            rule_code="FFR705",
            relative_path="reporting/fetch.py",
            source="def run_fetch() -> int:\n    return 0\n",
            expected_codes=("FFR705",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_tooling_when_checking_structure_then_enforces_tool_roles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="lowercase core rule code module name is flagged",
            rule_code="FFR706",
            relative_path="fensu/rules/fft104.py",
            source="",
            expected_codes=("FFR706",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="lowercase custom rule code module name is flagged",
            rule_code="FFR706",
            relative_path="fensu/rules/xjt001.py",
            source="",
            expected_codes=("FFR706",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="rule own lowercase code module name is flagged",
            rule_code="FFR706",
            relative_path="fensu/rules/ffr706.py",
            source="",
            expected_codes=("FFR706",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="descriptive rule module name is allowed",
            rule_code="FFR706",
            relative_path="fensu/rules/conditional_test_flow.py",
            source="",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="underscore-separated code-like module name is allowed",
            rule_code="FFR706",
            relative_path="fensu/rules/ffr_706.py",
            source="",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="code with suffix module name is allowed",
            rule_code="FFR706",
            relative_path="fensu/rules/fft104x.py",
            source="",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        FfrRuleTestCase(
            description="code-like module name outside rules role is allowed",
            rule_code="FFR706",
            relative_path="fensu/main/fft104.py",
            source="",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_rule_module_name_when_checking_roles_then_requires_descriptive_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FfrRuleTestCase(
            description="grouped helper models filename cannot claim the sibling models role",
            rule_code="FFR303",
            relative_path="commands/plan/_helpers/entry/models.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class PlanCommandRequest:\n"
                "    target: str\n"
            ),
            expected_codes=("FFR303",),
            expected_lines=(None,),
            expected_messages=(
                "reserved role filename 'models.py' cannot be nested beneath _helpers/",
            ),
            expected_paths=("commands/plan/_helpers/entry/models.py",),
        ),
        FfrRuleTestCase(
            description="helper types filename cannot claim the sibling types role",
            rule_code="FFR303",
            relative_path="commands/plan/_helpers/types.py",
            source="",
            expected_codes=("FFR303",),
            expected_lines=(None,),
            expected_messages=(
                "reserved role filename 'types.py' cannot be nested beneath _helpers/",
            ),
            expected_paths=("commands/plan/_helpers/types.py",),
        ),
        FfrRuleTestCase(
            description="helper constants filename cannot claim the sibling constants role",
            rule_code="FFR303",
            relative_path="commands/plan/_helpers/state/constants.py",
            source="",
            expected_codes=("FFR303",),
            expected_lines=(None,),
            expected_messages=(
                "reserved role filename 'constants.py' cannot be nested beneath _helpers/",
            ),
            expected_paths=("commands/plan/_helpers/state/constants.py",),
        ),
        FfrRuleTestCase(
            description="helper exceptions filename cannot claim the sibling exceptions role",
            rule_code="FFR303",
            relative_path="commands/plan/_helpers/errors/exceptions.py",
            source="",
            expected_codes=("FFR303",),
            expected_lines=(None,),
            expected_messages=(
                "reserved role filename 'exceptions.py' cannot be nested beneath _helpers/",
            ),
            expected_paths=("commands/plan/_helpers/errors/exceptions.py",),
        ),
        FfrRuleTestCase(
            description="sibling models role remains valid",
            rule_code="FFR303",
            relative_path="commands/plan/models.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="descriptive helper module remains valid",
            rule_code="FFR303",
            relative_path="commands/plan/_helpers/model_conversion.py",
            source="",
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="passive top-level leaf without main is rejected",
            rule_code="FFR309",
            relative_path="python_nodes/models.py",
            source="",
            expected_codes=("FFR309",),
            expected_lines=(None,),
            expected_messages=(
                "leaf runtime package 'python_nodes/' has no meaningful main/ entry module",
            ),
            expected_paths=("python_nodes/models.py",),
        ),
        FfrRuleTestCase(
            description="initializer-only main does not satisfy meaningful ownership",
            rule_code="FFR309",
            relative_path="python_nodes/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="placeholder main initializer",
                    relative_path="python_nodes/main/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("FFR309",),
            expected_lines=(None,),
            expected_messages=(
                "leaf runtime package 'python_nodes/' has no meaningful main/ entry module",
            ),
            expected_paths=("python_nodes/models.py",),
        ),
        FfrRuleTestCase(
            description="top-level leaf with a focused main entry is valid",
            rule_code="FFR309",
            relative_path="compiler/models.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="compiler entry",
                    relative_path="compiler/main/compile_project.py",
                    source="def compile_project() -> None:\n    return None\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="branch parent does not need main when its subdomain owns behavior",
            rule_code="FFR309",
            relative_path="commands/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="plan entry",
                    relative_path="commands/plan/main/run_plan.py",
                    source="def run_plan() -> None:\n    return None\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        FfrRuleTestCase(
            description="passive subdomain without main is rejected",
            rule_code="FFR309",
            relative_path="commands/__init__.py",
            source="",
            support_files=(
                FfrSupportFile(
                    description="orphan plan contracts",
                    relative_path="commands/plan/models.py",
                    source="",
                ),
            ),
            expected_codes=("FFR309",),
            expected_lines=(None,),
            expected_messages=(
                "leaf runtime package 'commands/plan/' has no meaningful main/ entry module",
            ),
            expected_paths=("commands/plan/models.py",),
        ),
        FfrRuleTestCase(
            description="tooling package is outside the runtime leaf-main policy",
            rule_code="FFR309",
            relative_path="release/models.py",
            source="",
            scope=ScopeName.TOOLING,
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_runtime_ownership_path_when_checking_then_enforces_role_and_main_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    scope_root: Path = (
        tmp_path / {False: "src/pkg", True: "scripts"}[test_case.scope is ScopeName.TOOLING]
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert tuple(fault.path.relative_to(scope_root).as_posix() for fault in result.faults) == (
        test_case.expected_paths
    )
