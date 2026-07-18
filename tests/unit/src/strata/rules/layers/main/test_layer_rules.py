"""Tests for layer boundary rules."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from strata.config.models import Config
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from tests.unit.src.strata.rules.layers.main import helpers as layer_test_helpers
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
            files=(("src/pkg/domain/alpha/main/run.py", "from .._helpers import local\n"),),
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
                    "from pkg.domain.beta._helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL101",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="sibling helper internals are flagged under a python container",
            rule_code="SFL101",
            files=(
                (
                    "python/mypkg/domain/alpha/main/run.py",
                    "from mypkg.domain.beta._helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL101",),
            expected_lines=(1,),
            roots=("python/mypkg",),
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
                    "from pkg.domain.alpha._helpers.parse import parse_value\n",
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
                    "from pkg.domain_b.core._helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL102",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="cross-domain helper import is flagged under a lib container",
            rule_code="SFL102",
            files=(
                (
                    "lib/acme/domain_a/core/main/run.py",
                    "from acme.domain_b.core._helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL102",),
            expected_lines=(1,),
            roots=("lib/acme",),
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
                    "from pkg.domain_a.other._helpers.parse import parse_value\n",
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
        LayerRuleTestCase(
            description="shipped custom-rule exemplar may consume the public package API",
            rule_code="SFL103",
            files=(
                (
                    "src/pkg/rules/exemplars/main/annotations/_parameter_annotation.py",
                    "from pkg import Family, RuleContext, rule\n",
                ),
            ),
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
            description="private main entry is available across subdomains in its domain",
            rule_code="SFL104",
            files=(
                (
                    "src/pkg/orders/billing/main/_calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "src/pkg/orders/shipping/_helpers/use.py",
                    "from pkg.orders.billing.main._calculate import calculate\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="private main entry rejects an importer from another domain",
            rule_code="SFL104",
            files=(
                (
                    "src/pkg/orders/billing/main/_calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "src/pkg/inventory/_helpers/use.py",
                    "from pkg.orders.billing.main._calculate import calculate\n",
                ),
            ),
            expected_codes=("SFL104",),
            expected_lines=(1,),
            expected_messages=(
                "import 'pkg.orders.billing.main._calculate' reaches a domain-private main entry",
            ),
        ),
        LayerRuleTestCase(
            description="private main entry rejects a from-main submodule import across domains",
            rule_code="SFL104",
            files=(
                (
                    "src/pkg/orders/billing/main/_calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "src/pkg/inventory/_helpers/use.py",
                    "from pkg.orders.billing.main import _calculate\n",
                ),
            ),
            expected_codes=("SFL104",),
            expected_lines=(1,),
            expected_messages=(
                "import 'pkg.orders.billing.main._calculate' reaches a domain-private main entry",
            ),
        ),
        LayerRuleTestCase(
            description="private main entry rejects a tooling importer",
            rule_code="SFL104",
            files=(
                (
                    "src/pkg/orders/billing/main/_calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "scripts/use_orders.py",
                    "from pkg.orders.billing.main._calculate import calculate\n",
                ),
            ),
            tooling=("scripts",),
            expected_codes=("SFL104",),
            expected_lines=(1,),
            expected_messages=(
                "import 'pkg.orders.billing.main._calculate' reaches a domain-private main entry",
            ),
        ),
        LayerRuleTestCase(
            description="private main entry remains available to mirrored tests",
            rule_code="SFL104",
            files=(
                (
                    "src/pkg/orders/billing/main/_calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "tests/unit/src/pkg/orders/billing/main/test_calculate.py",
                    "from pkg.orders.billing.main._calculate import calculate\n",
                ),
            ),
            tests=("tests",),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_domain_private_main_entry_when_importing_then_enforces_domain_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="public main entry without importers must become domain-private",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
            ),
            expected_codes=("SFL105",),
            expected_lines=(None,),
            expected_messages=("public main entry has no importer outside its owning domain",),
        ),
        LayerRuleTestCase(
            description="same-domain importer does not justify a public main entry",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "src/pkg/orders/shipping/_helpers/use.py",
                    "from pkg.orders.billing.main.calculate import calculate\n",
                ),
            ),
            expected_codes=("SFL105",),
            expected_lines=(None,),
            expected_messages=("public main entry has no importer outside its owning domain",),
        ),
        LayerRuleTestCase(
            description="another domain importer justifies a public main entry",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "src/pkg/inventory/_helpers/use.py",
                    "from pkg.orders.billing.main.calculate import calculate\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="from-main import by another domain justifies a public main entry",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "src/pkg/inventory/_helpers/use.py",
                    "from pkg.orders.billing.main import calculate\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="tooling importer justifies a public main entry",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "scripts/use_orders.py",
                    "from pkg.orders.billing.main.calculate import calculate\n",
                ),
            ),
            tooling=("scripts",),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="root package stub importer justifies a public main entry",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "src/pkg/__init__.pyi",
                    "from pkg.orders.billing.main.calculate import calculate as calculate\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="project script declaration justifies a public main entry",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "pyproject.toml",
                    '[project]\nname = "pkg"\n[project.scripts]\ncalculate = '
                    '"pkg.orders.billing.main.calculate:calculate"\n',
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="test importer does not justify a public main entry",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
                (
                    "tests/unit/src/pkg/orders/billing/main/test_calculate.py",
                    "from pkg.orders.billing.main.calculate import calculate\n",
                ),
            ),
            tests=("tests",),
            expected_codes=("SFL105",),
            expected_lines=(None,),
            expected_messages=("public main entry has no importer outside its owning domain",),
        ),
        LayerRuleTestCase(
            description="domain-private main entry does not require external use",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/_calculate.py",
                    "def calculate() -> None:\n    pass\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="main package initializer is not an entry module",
            rule_code="SFL105",
            files=(
                (
                    "src/pkg/orders/billing/main/commands/__init__.py",
                    '"""Billing command entries."""\n',
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_main_entry_visibility_when_checking_external_use_then_requires_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            description="helper-private class stays local in own file",
            rule_code="SFL110",
            files=(("src/pkg/domain/alpha/_helpers/parse.py", "class _Cursor:\n    pass\n"),),
            expected_codes=(),
            expected_lines=(),
        ),
        LayerRuleTestCase(
            description="helper-private class imported by main is flagged",
            rule_code="SFL110",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha._helpers.parse import _Cursor\n",
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
                    "src/pkg/domain/alpha/_helpers/format.py",
                    "from pkg.domain.alpha._helpers.parse import _Cursor\n",
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
                    "from pkg.domain.alpha._helpers import parse\nvalue = parse._Cursor()\n",
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
        LayerRuleTestCase(
            description="native SFL001 bypasses its Python core callback",
            rule_code="SFL001",
            files=(("src/pkg/domain/alpha/main/run.py", "from ..models import Result\n"),),
            expected_codes=("SFL001",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="native SFL002 bypasses its Python core callback",
            rule_code="SFL002",
            files=(("src/pkg/domain/alpha/main/run.py", "from pkg.models import *\n"),),
            expected_codes=("SFL002",),
            expected_lines=(1,),
        ),
        LayerRuleTestCase(
            description="native SFL110 bypasses its Python core callback",
            rule_code="SFL110",
            files=(
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha._helpers.parse import _Cursor\n",
                ),
            ),
            expected_codes=("SFL110",),
            expected_lines=(1,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_registered_native_layer_rule_when_evaluating_then_skips_python_callback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayerRuleTestCase,
) -> None:
    python_callback: Mock = Mock(side_effect=AssertionError("Python callback executed"))
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in layer_test_helpers.SFL_RULES}
    monkeypatch.setattr(
        layer_test_helpers,
        "SFL_RULES",
        (replace(rules_by_code[test_case.rule_code], check=python_callback),),
    )

    result: EvaluationResult = evaluate_layer_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert python_callback.call_count == 0


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
        ),
        ToolingImportRuleTestCase(
            description="runtime import follows a nested configured tooling package",
            files=(
                ("src/pkg/domain/alpha/main/run.py", "from tools.release import publish\n"),
                ("dev/tools/release.py", "def publish() -> None:\n    pass\n"),
            ),
            tooling=("dev/tools",),
            expected_codes=("SFL301",),
            expected_lines=(1,),
        ),
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
                    "from pkg.domain_b.core._helpers.parse import parse_value\n",
                ),
            ),
            expected_codes=("SFL102",),
            expected_lines=(1,),
            expected_messages=(
                "import 'pkg.domain_b.core._helpers.parse' reaches into internal structure of "
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
