"""Tests for layer boundary rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.core.models import Config
from strata.evaluation.core.models import EvaluationResult
from tests.unit.src.strata.rules.layers.main._test_types import (
    LayerRuleTestCase,
    ToolingImportRuleTestCase,
)
from tests.unit.src.strata.rules.layers.main.helpers import (
    evaluate_layer_rule,
    evaluate_layer_test_case,
    write_files,
)


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="relative import from current package is flagged",
            rule_code="SFL001",
            files=(("src/pkg/domain/alpha/main/run.py", "from . import local\n"),),
            expected_codes=("SFL001",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="relative import from parent package is flagged",
            rule_code="SFL001",
            files=(("src/pkg/domain/alpha/main/run.py", "from ..helpers import local\n"),),
            expected_codes=("SFL001",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="absolute import is allowed",
            rule_code="SFL001",
            files=(
                ("src/pkg/domain/alpha/main/run.py", "from pkg.domain.alpha.models import Model\n"),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_imports_when_checking_absolute_imports_then_flags_only_relative_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="absolute star import is flagged",
            rule_code="SFL002",
            files=(
                ("src/pkg/domain/alpha/main/run.py", "from pkg.domain.alpha.models import *\n"),
            ),
            expected_codes=("SFL002",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="relative star import is flagged independently of import direction",
            rule_code="SFL002",
            files=(("src/pkg/domain/alpha/main/run.py", "from ..models import *\n"),),
            expected_codes=("SFL002",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="explicit imported names are allowed",
            rule_code="SFL002",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha.models import First, Second\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="ordinary module import is allowed",
            rule_code="SFL002",
            files=(("src/pkg/domain/alpha/main/run.py", "import pkg.domain.alpha.models\n"),),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_imports_when_checking_star_imports_then_flags_only_wildcards(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="sibling helper internals are flagged",
            rule_code="SFL101",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.beta.helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL101",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="sibling main entry is allowed",
            rule_code="SFL101",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.beta.main.load import load\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="sibling role file is allowed",
            rule_code="SFL101",
            files=(
                ("src/pkg/domain/alpha/main/run.py", "from pkg.domain.beta.models import Model\n"),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="same subpackage helper import is allowed",
            rule_code="SFL101",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha.helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_sibling_imports_when_checking_layers_then_flags_only_internal_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="cross-domain helper import is flagged",
            rule_code="SFL102",
            files=(
                (
                    "src/pkg/domain_a/core/main/run.py",
                    "from pkg.domain_b.core.helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL102",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="cross-domain role file import is allowed",
            rule_code="SFL102",
            files=(
                (
                    "src/pkg/domain_a/core/main/run.py",
                    "from pkg.domain_b.core.models import Model\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="same-domain helper import is allowed",
            rule_code="SFL102",
            files=(
                (
                    "src/pkg/domain_a/core/main/run.py",
                    "from pkg.domain_a.other.helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_cross_package_imports_when_checking_layers_then_flags_only_internal_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="internal from-import through bare package is flagged",
            rule_code="SFL103",
            files=(("src/pkg/domain/alpha/main/run.py", "from pkg import PublicModel\n"),),
            expected_codes=("SFL103",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="internal plain import of bare package is flagged",
            rule_code="SFL103",
            files=(("src/pkg/domain/alpha/main/run.py", "import pkg\n"),),
            expected_codes=("SFL103",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="internal aliased import of bare package is flagged",
            rule_code="SFL103",
            files=(("src/pkg/domain/alpha/main/run.py", "import pkg as public_api\n"),),
            expected_codes=("SFL103",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="internal import from concrete owning module is allowed",
            rule_code="SFL103",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha.models import Model\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="root public surface may import package internals",
            rule_code="SFL103",
            files=(("src/pkg/__init__.py", "from pkg.domain.alpha.models import Model\n"),),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_internal_imports_when_checking_public_surface_then_flags_bare_package_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="helper-private class stays local in own file",
            rule_code="SFL110",
            files=(("src/pkg/domain/alpha/helpers/parse.py", "class _Cursor:\n    pass\n"),),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="helper-private class imported by main is flagged",
            rule_code="SFL110",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha.helpers.parse import _Cursor\n",
                ),
            ),
            expected_codes=("SFL110",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="helper-private class imported by sibling helper is flagged",
            rule_code="SFL110",
            files=(
                (
                    "src/pkg/domain/alpha/helpers/format.py",
                    "from pkg.domain.alpha.helpers.parse import _Cursor\n",
                ),
            ),
            expected_codes=("SFL110",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="helper-private class module qualified reference is flagged",
            rule_code="SFL110",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha.helpers import parse\nvalue = parse._Cursor()\n",
                ),
            ),
            expected_codes=("SFL110",),
            expected_lines=(2,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_helper_private_class_references_when_checking_layers_then_flags_cross_file_use(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ToolingImportRuleTestCase(
            description="runtime import from tooling is flagged while tooling import is allowed",
            files=(
                ("src/pkg/domain/alpha/main/run.py", "from scripts.tools import helper\n"),
                ("scripts/tooling.py", "from scripts.tools import helper\n"),
            ),
            tooling=("scripts",),
            expected_codes=("SFL301",),
            expected_lines=(1,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_runtime_imports_tooling_when_checking_layers_then_flags_only_runtime_import(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ToolingImportRuleTestCase,
) -> None:
    write_files(root=tmp_path, files=test_case.files)
    config: Config = Config(roots=("src/pkg",), tests=(), tooling=test_case.tooling)

    result: EvaluationResult = evaluate_layer_rule(
        rule_code="SFL301", config=config, monkeypatch=monkeypatch, repo_root=tmp_path
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="cross-package diagnostic identifies the imported internal path",
            rule_code="SFL102",
            files=(
                (
                    "src/pkg/domain_a/core/main/run.py",
                    "from pkg.domain_b.core.helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL102",),
            expected_lines=(1,),
            expected_messages=(
                "import 'pkg.domain_b.core.helpers.parse' reaches into internal structure of "
                "'pkg.domain_b'",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cross_package_internal_import_when_evaluating_then_names_target_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
