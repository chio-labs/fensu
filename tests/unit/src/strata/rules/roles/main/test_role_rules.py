"""Tests for roles rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.analysis.models import ProjectDependency
from strata.analysis.types import ProjectDependencyKind
from strata.config.models import ThresholdOverride
from strata.discovery.types import ScopeName
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.types import Threshold
from tests.unit.src.strata.rules.roles.main._test_types import (
    ContainerDepthScaleTestCase,
    ContainerScaleTestCase,
    SfrRuleTestCase,
    SfrSupportFile,
)
from tests.unit.src.strata.rules.roles.main.helpers import (
    anchor_dependencies,
    evaluate_flat_helpers_scale,
    evaluate_role_bucket_depth_scale,
    evaluate_role_test_case,
)


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
            description="private dataclass protocol in types role is flagged as a model",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source=(
                "from dataclasses import dataclass\n"
                "from typing import Protocol\n\n"
                "@dataclass\n"
                "class _Event(Protocol):\n"
                "    value: int\n"
            ),
            expected_codes=("SFR002",),
            expected_lines=(5,),
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
            description="unanchored outer generic package does not hide anchored nested package",
            rule_code="SFR204",
            relative_path="shared/zeta/misc/value.py",
            source="value: int = 1\n",
            support_files=(
                SfrSupportFile(
                    description="outer shared package anchor",
                    relative_path="shared/alpha/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR204", "SFR204"),
            expected_lines=(None, None),
            expected_messages=(
                "shared/ does not identify an owner; name the business or technical capability",
                "misc/ does not identify an owner; name the business or technical capability",
            ),
            expected_paths=("shared/alpha/models.py", "shared/zeta/misc/value.py"),
        ),
        SfrRuleTestCase(
            description="one anchor reports every nested generic package",
            rule_code="SFR204",
            relative_path="domain/util/utils/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204", "SFR204"),
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
    test_case: SfrRuleTestCase,
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
        SfrRuleTestCase(
            description="dataclass outside models role is flagged",
            rule_code="SFR101",
            relative_path="domain/core/_helpers/results.py",
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
            relative_path="domain/core/_helpers/service.py",
            source="from typing import Protocol\n\nclass _Service(Protocol):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="private dataclass protocol outside types is not a type declaration",
            rule_code="SFR102",
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
        SfrRuleTestCase(
            description="explicit TypeAlias outside types role is flagged",
            rule_code="SFR102",
            relative_path="domain/core/_helpers/aliases.py",
            source=(
                "from typing import Literal, TypeAlias\n\n"
                "PathMode: TypeAlias = Literal['short', 'full']\n"
            ),
            expected_codes=("SFR102",),
            expected_lines=(3,),
        ),
        SfrRuleTestCase(
            description="public uppercase constant outside constants role is flagged",
            rule_code="SFR103",
            relative_path="domain/core/_helpers/values.py",
            source="DEFAULT_VALUE: int = 1\n",
            expected_codes=("SFR103",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="private uppercase constant outside constants role is allowed",
            rule_code="SFR103",
            relative_path="domain/core/_helpers/values.py",
            source="_DEFAULT_VALUE: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="custom error outside exceptions role is flagged",
            rule_code="SFR104",
            relative_path="domain/core/_helpers/errors.py",
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
            relative_path="domain/core/_helpers/misc.py",
            source="value: int = 1\n",
            expected_codes=("SFR201",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="common filename inside an owned role is allowed",
            rule_code="SFR201",
            relative_path="domain/core/_helpers/common.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="shared domain package is flagged",
            rule_code="SFR204",
            relative_path="shared/core/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="legacy helpers package is rejected instead of treated as a role",
            rule_code="SFR204",
            relative_path="domain/core/helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="shared subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/shared/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="shared package deeper than subdomain is flagged",
            rule_code="SFR204",
            relative_path="domain/orders/_helpers/shared/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="common domain package is flagged",
            rule_code="SFR204",
            relative_path="common/core/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="util domain package is flagged",
            rule_code="SFR204",
            relative_path="util/core/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="utils subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/utils/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="misc subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/misc/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="base subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/base/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="lib subdomain package is flagged",
            rule_code="SFR204",
            relative_path="domain/lib/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="generic package name inside helpers role is flagged",
            rule_code="SFR204",
            relative_path="domain/core/_helpers/utils/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="deeper misc package is flagged",
            rule_code="SFR204",
            relative_path="domain/orders/_helpers/parsing/misc/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="deeper util package is flagged",
            rule_code="SFR204",
            relative_path="domain/orders/_helpers/parsing/util/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR204",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="generic module filename is not treated as a package",
            rule_code="SFR204",
            relative_path="domain/orders/_helpers/misc.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="tooling generic package names remain outside runtime package rule",
            rule_code="SFR204",
            relative_path="shared/_helpers/value.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="domain-specific package names are allowed",
            rule_code="SFR204",
            relative_path="orders/compile/_helpers/value.py",
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
            relative_path="domain/core/_helpers/service.py",
            source="class Service:\n    value: int\n",
            expected_codes=("SFR205",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="private plain class in helpers is allowed",
            rule_code="SFR205",
            relative_path="domain/core/_helpers/service.py",
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
            relative_path="domain/core/_helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="flat helper",
                    relative_path="domain/core/_helpers/values.py",
                    source="value: int = 1\n",
                ),
                SfrSupportFile(
                    description="helper concern",
                    relative_path="domain/core/_helpers/parsing/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("SFR301",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="helpers package over flat threshold is flagged",
            rule_code="SFR301",
            relative_path="domain/core/_helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="first helper",
                    relative_path="domain/core/_helpers/first.py",
                    source="value: int = 1\n",
                ),
                SfrSupportFile(
                    description="second helper",
                    relative_path="domain/core/_helpers/second.py",
                    source="value: int = 2\n",
                ),
            ),
            thresholds={Threshold.MAX_HELPERS_CONTAINER_MODULES: 1},
            expected_codes=("SFR301",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="flat helpers package under threshold is allowed",
            rule_code="SFR301",
            relative_path="domain/core/_helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="flat helper",
                    relative_path="domain/core/_helpers/values.py",
                    source="value: int = 1\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="main role-named bucket is flagged",
            rule_code="SFR302",
            relative_path="domain/core/main/_helpers/value.py",
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
            relative_path="domain/core/_helpers/parsing.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="shared package has no nested structural exception",
            rule_code="SFR305",
            relative_path="domain/core/shared/value.py",
            source="value: int = 1\n",
            expected_codes=("SFR305",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="leaf ignores direct asset data and empty directories",
            rule_code="SFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="direct main role content",
                    relative_path="domain/main/run.py",
                    source="def run() -> None:\n    return None\n",
                ),
                SfrSupportFile(
                    description="asset directory without Python",
                    relative_path="domain/assets/logo.svg",
                    source="<svg/>\n",
                ),
                SfrSupportFile(
                    description="data directory without Python",
                    relative_path="domain/data/records.json",
                    source="[]\n",
                ),
                SfrSupportFile(
                    description="empty directory",
                    relative_path="domain/empty",
                    source="",
                    is_directory=True,
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="asset directory becomes a named subdomain when Python source appears",
            rule_code="SFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="asset namespace Python source",
                    relative_path="domain/assets/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="top-level domain with named subdomains is a legal branch",
            rule_code="SFR306",
            relative_path="domain/orders/models.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="second named subdomain",
                    relative_path="domain/customers/main/read.py",
                    source="def read() -> None:\n    return None\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="top-level domain mixing direct main role and named subdomain is flagged",
            rule_code="SFR306",
            relative_path="domain/main/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                SfrSupportFile(
                    description="named subdomain role file",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="top-level domain mixing direct role file and named subdomain is flagged",
            rule_code="SFR306",
            relative_path="domain/types.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="named subdomain role file",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="shared top-level domain follows mixed domain semantics",
            rule_code="SFR306",
            relative_path="shared/models.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="named subdomain below shared domain",
                    relative_path="shared/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="shared direct child is a named subdomain for domain shape",
            rule_code="SFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="banned shared subdomain",
                    relative_path="domain/shared/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR306",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="role file below subpackage remains allowed",
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
        SfrRuleTestCase(
            description="direct domain role module does not require a subdomain",
            rule_code="SFR307",
            relative_path="domain/main.py",
            source="def main() -> None:\n    return None\n",
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
            description="helpers bucket module cap reports observed and effective values",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="bucket init",
                    relative_path="domain/orders/_helpers/parsing/__init__.py",
                    source="",
                ),
                SfrSupportFile(
                    description="first module",
                    relative_path="domain/orders/_helpers/parsing/first.py",
                    source="",
                ),
                SfrSupportFile(
                    description="second module",
                    relative_path="domain/orders/_helpers/parsing/second.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_HELPERS_CONTAINER_MODULES: 1},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ container has 2 modules; effective limit is 1",),
            expected_paths=("domain/orders/_helpers/parsing/__init__.py",),
        ),
        SfrRuleTestCase(
            description="matching override raises bucket module cap at reported anchor",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="bucket init",
                    relative_path="domain/orders/_helpers/parsing/__init__.py",
                    source="",
                ),
                SfrSupportFile(
                    description="first module",
                    relative_path="domain/orders/_helpers/parsing/first.py",
                    source="",
                ),
                SfrSupportFile(
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
        SfrRuleTestCase(
            description="namespace helpers root anchors one deep bucket fault",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/parsing/text/read.py",
            source="def read() -> None:\n    return None\n",
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket depth is 2; effective limit is 1",),
            expected_paths=("domain/orders/_helpers/parsing/text/read.py",),
        ),
        SfrRuleTestCase(
            description="main grouped bucket enforces its own module cap",
            rule_code="SFR302",
            relative_path="domain/orders/main/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="bucket init",
                    relative_path="domain/orders/main/commands/__init__.py",
                    source="",
                ),
                SfrSupportFile(
                    description="first command",
                    relative_path="domain/orders/main/commands/first.py",
                    source="",
                ),
                SfrSupportFile(
                    description="second command",
                    relative_path="domain/orders/main/commands/second.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_MAIN_CONTAINER_MODULES: 1},
            expected_codes=("SFR302",),
            expected_lines=(None,),
            expected_messages=("main/ container has 2 modules; effective limit is 1",),
            expected_paths=("domain/orders/main/commands/__init__.py",),
        ),
        SfrRuleTestCase(
            description="role-named bucket is faulted once from the outer helpers root",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/read.py",
            source="def read() -> None:\n    return None\n",
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/read.py",),
        ),
        SfrRuleTestCase(
            description="nested main bucket is faulted once with raised depth",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="nested helpers bucket is faulted once with raised depth",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/_helpers/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket '_helpers/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/_helpers/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="nested classes bucket is faulted once with raised depth",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/classes/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'classes/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/classes/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="nested models bucket is faulted once with raised depth",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/models/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'models/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/models/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="nested types bucket is faulted once with raised depth",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/types/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'types/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/types/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="nested constants bucket is faulted once with raised depth",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/constants/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'constants/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/constants/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="nested exceptions bucket is faulted once with raised depth",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/exceptions/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'exceptions/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/exceptions/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="nested role bucket is also detected below main",
            rule_code="SFR302",
            relative_path="domain/orders/main/classes/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR302",),
            expected_lines=(None,),
            expected_messages=("main/ bucket 'classes/' uses a runtime role name",),
            expected_paths=("domain/orders/main/classes/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="ancestor role bucket initializer owns fault instead of descendant anchor",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            support_files=(
                SfrSupportFile(
                    description="forbidden bucket initializer",
                    relative_path="domain/orders/_helpers/main/__init__.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/__init__.py",),
        ),
        SfrRuleTestCase(
            description="direct Python file owns role bucket fault before descendants",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            support_files=(
                SfrSupportFile(
                    description="direct bucket module",
                    relative_path="domain/orders/_helpers/main/owner.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301", "SFR301"),
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
        SfrRuleTestCase(
            description="lexicographically first direct Python file owns role bucket fault",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/zulu.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="lexically first direct module",
                    relative_path="domain/orders/_helpers/main/alpha.py",
                    source="",
                ),
            ),
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/alpha.py",),
        ),
        SfrRuleTestCase(
            description="lexicographically first descendant owns namespace role bucket fault",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/zulu/read.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="lexically first descendant module",
                    relative_path="domain/orders/_helpers/main/alpha/read.py",
                    source="",
                ),
            ),
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/alpha/read.py",),
        ),
        SfrRuleTestCase(
            description="multiple invalid segments each emit one bucket-owned fault",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/classes/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR301", "SFR301"),
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
        SfrRuleTestCase(
            description="nested generic shared bucket remains only SFR204 ownership",
            rule_code="SFR",
            relative_path="domain/orders/_helpers/shared/parsing/read.py",
            source="def read() -> None:\n    return None\n",
            thresholds={Threshold.MAX_ROLE_DEPTH: 2},
            expected_codes=("SFR204",),
            expected_lines=(None,),
            expected_messages=(
                "shared/ does not identify an owner; name the business or technical capability",
            ),
            expected_paths=("domain/orders/_helpers/shared/parsing/read.py",),
        ),
        SfrRuleTestCase(
            description="namespace helpers root detects init-only role-named bucket",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/main/__init__.py",
            source="",
            expected_codes=("SFR301",),
            expected_lines=(None,),
            expected_messages=("_helpers/ bucket 'main/' uses a runtime role name",),
            expected_paths=("domain/orders/_helpers/main/__init__.py",),
        ),
        SfrRuleTestCase(
            description="generic and asset buckets do not create SFR301 faults",
            rule_code="SFR301",
            relative_path="domain/orders/_helpers/__init__.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="generic bucket",
                    relative_path="domain/orders/_helpers/misc/read.py",
                    source="",
                ),
                SfrSupportFile(
                    description="asset",
                    relative_path="domain/orders/_helpers/assets/logo.svg",
                    source="<svg/>",
                ),
                SfrSupportFile(
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
    test_case: SfrRuleTestCase,
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
        ContainerDepthScaleTestCase(
            description="tenfold namespace depth keeps bucket anchor queries compact and linear",
            small_depth=10,
            large_depth=100,
            expected_max_query_multiplier=11,
            expected_max_inspection_multiplier=11,
            expected_fault_count=1,
            expected_max_anchor_answer_paths=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_deeper_role_bucket_when_evaluating_then_anchor_queries_remain_compact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ContainerDepthScaleTestCase,
) -> None:
    small, small_inspections = evaluate_role_bucket_depth_scale(
        project_root=tmp_path / "small-depth",
        depth=test_case.small_depth,
        monkeypatch=monkeypatch,
    )
    large, large_inspections = evaluate_role_bucket_depth_scale(
        project_root=tmp_path / "large-depth",
        depth=test_case.large_depth,
        monkeypatch=monkeypatch,
    )
    small_queries: tuple[ProjectDependency, ...] = anchor_dependencies(small)
    large_queries: tuple[ProjectDependency, ...] = anchor_dependencies(large)

    assert len(small.faults) == test_case.expected_fault_count
    assert len(large.faults) == test_case.expected_fault_count
    assert len(large_queries) <= len(small_queries) * test_case.expected_max_query_multiplier
    assert large_inspections <= small_inspections * test_case.expected_max_inspection_multiplier
    assert all(
        isinstance(dependency.answer, tuple)
        and len(dependency.answer) <= test_case.expected_max_anchor_answer_paths
        for dependency in (*small_queries, *large_queries)
    )


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="helpers main bucket has no secondary entry or main-shape faults",
            rule_code="SF",
            relative_path="domain/orders/_helpers/main/read.py",
            source="def _prepare() -> None:\n    value: int = build()\n",
            thresholds={
                Threshold.MAX_STATEMENTS: 0,
                Threshold.MAX_DISTINCT_CALLS: 0,
                Threshold.MAX_LOCALS: 0,
            },
            expected_codes=("SFR301",),
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
    test_case: SfrRuleTestCase,
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
        SfrRuleTestCase(
            description="mixed domain anchors one fault at its init module",
            rule_code="SFR306",
            relative_path="domain/models.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="domain init anchor",
                    relative_path="domain/__init__.py",
                    source="",
                ),
                SfrSupportFile(
                    description="named subdomain",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR306",),
            expected_lines=(None,),
            expected_paths=("domain/__init__.py",),
        ),
        SfrRuleTestCase(
            description="mixed domain without init anchors one fault at first Python file",
            rule_code="SFR306",
            relative_path="domain/types.py",
            source="",
            support_files=(
                SfrSupportFile(
                    description="lexically first named subdomain file",
                    relative_path="domain/orders/models.py",
                    source="",
                ),
            ),
            expected_codes=("SFR306",),
            expected_lines=(None,),
            expected_paths=("domain/orders/models.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_top_level_domain_when_checking_then_anchors_one_deterministic_fault(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
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
            description="grouped main module is checked as an entry",
            rule_code="SFR401",
            relative_path="domain/core/main/commands/run.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("SFR401",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="main.py under main is checked as an entry",
            rule_code="SFR401",
            relative_path="domain/core/main/main.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("SFR401",),
            expected_lines=(None,),
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
            relative_path="domain/core/_helpers/values.py",
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
        SfrRuleTestCase(
            description="grouped main entry colliding with package is flagged",
            rule_code="SFR405",
            relative_path="domain/core/main/commands/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                SfrSupportFile(
                    description="grouped colliding package",
                    relative_path="domain/core/main/commands/run/__init__.py",
                    source="",
                ),
            ),
            expected_codes=("SFR405",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="flat main entry sharing its name with a file is allowed",
            rule_code="SFR405",
            relative_path="domain/core/main/run.py",
            source="def run() -> None:\n    return None\n",
            support_files=(
                SfrSupportFile(
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
            relative_path="domain/core/_helpers/main.py",
            source="def run() -> None:\n    return None\n",
            expected_codes=("SFR502",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="shallow helper concern module is allowed",
            rule_code="SFR502",
            relative_path="domain/core/_helpers/parsing/values.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="deep helper concern module depth belongs to SFR301",
            rule_code="SFR502",
            relative_path="domain/core/_helpers/parsing/text/values.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="private constant after function is flagged",
            rule_code="SFR503",
            relative_path="domain/core/_helpers/values.py",
            source="def run() -> None:\n    return None\n\n_VALUE: int = 1\n",
            expected_codes=("SFR503",),
            expected_lines=(4,),
        ),
        SfrRuleTestCase(
            description="private constant before function is allowed",
            rule_code="SFR503",
            relative_path="domain/core/_helpers/values.py",
            source="_VALUE: int = 1\n\ndef run() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="source above configured line limit is flagged",
            rule_code="SFR601",
            relative_path="domain/core/_helpers/values.py",
            source="first: int = 1\nsecond: int = 2\nthird: int = 3\n",
            thresholds={Threshold.MAX_FILE_LINES: 2},
            expected_codes=("SFR601",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="source at configured line limit is allowed",
            rule_code="SFR601",
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
            description="path-level entry fault inherits actionable catalogue remediation",
            rule_code="SFR401",
            relative_path="domain/core/main/run.py",
            source="def _prepare() -> None:\n    return None\n",
            expected_codes=("SFR401",),
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
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert tuple(fault.remediation for fault in result.faults) == test_case.expected_remediations


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="direct script with private parser and public main is allowed",
            rule_code="SFR701",
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
        SfrRuleTestCase(
            description="public parse_args in direct script is flagged",
            rule_code="SFR701",
            relative_path="generate_report.py",
            source=(
                "def parse_args() -> object:\n"
                "    return object()\n\n"
                "def main() -> int:\n"
                "    return 0\n"
            ),
            expected_codes=("SFR701",),
            expected_lines=(1,),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="class in direct script is flagged",
            rule_code="SFR701",
            relative_path="generate_report.py",
            source="class Fetcher:\n    pass\n\ndef main() -> int:\n    return 0\n",
            expected_codes=("SFR701",),
            expected_lines=(1,),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="direct script calling imported tooling main entry is allowed",
            rule_code="SFR702",
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
        SfrRuleTestCase(
            description="direct script without main delegation is flagged",
            rule_code="SFR702",
            relative_path="generate_report.py",
            source="def main() -> int:\n    return 0\n",
            expected_codes=("SFR702",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="implementation call retained in direct script main is flagged",
            rule_code="SFR702",
            relative_path="generate_report.py",
            source=(
                "import json\n"
                "from scripts.reporting.main.fetch import run_fetch\n\n"
                "def main() -> int:\n"
                "    result: object = run_fetch()\n"
                "    print(json.dumps(result))\n"
                "    return 0\n"
            ),
            expected_codes=("SFR702", "SFR702"),
            expected_lines=(6, 6),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="direct script above configured line limit is flagged",
            rule_code="SFR703",
            relative_path="generate_report.py",
            source="def main() -> int:\n    value: int = 1\n    return value\n",
            thresholds={Threshold.MAX_SCRIPT_ENTRYPOINT_LINES: 2},
            expected_codes=("SFR703",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="rules role allows multiple decorated functions",
            rule_code="SFR704",
            relative_path="strata_rules/rules/imports.py",
            source=(
                "from strata import Family, rule\n\n"
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
        SfrRuleTestCase(
            description="undecorated function in rules role is flagged",
            rule_code="SFR704",
            relative_path="strata_rules/rules/imports.py",
            source="def helper() -> None:\n    return None\n",
            expected_codes=("SFR704",),
            expected_lines=(1,),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="standard role directory directly under tool package is allowed",
            rule_code="SFR705",
            relative_path="reporting/main/fetch.py",
            source="def run_fetch() -> int:\n    return 0\n",
            expected_codes=(),
            expected_lines=(),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="arbitrary package directly under tool package is flagged",
            rule_code="SFR705",
            relative_path="reporting/work/fetch.py",
            source="def run_fetch() -> int:\n    return 0\n",
            expected_codes=("SFR705",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
        SfrRuleTestCase(
            description="direct implementation module under tool package is flagged",
            rule_code="SFR705",
            relative_path="reporting/fetch.py",
            source="def run_fetch() -> int:\n    return 0\n",
            expected_codes=("SFR705",),
            expected_lines=(None,),
            scope=ScopeName.TOOLING,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_tooling_when_checking_structure_then_enforces_tool_roles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
