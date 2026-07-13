"""Tests for structural import ownership inference."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.models import EvaluationResult
from strata.rules.layers._helpers.imports import classify_module_ownership
from strata.rules.layers.models import ModuleOwnership
from tests.unit.src.strata.rules.layers.main._test_types import (
    LayerRuleTestCase,
    LayoutImportConsistencyTestCase,
    OwnershipClassificationTestCase,
)
from tests.unit.src.strata.rules.layers.main.helpers import (
    evaluate_layer_test_case,
    evaluate_layout_import_consistency,
)


@pytest.mark.parametrize(
    "test_case",
    [
        OwnershipClassificationTestCase(
            description="first role locks ownership before role-looking tail buckets",
            module_parts=("pkg", "domain", "owner", "_helpers", "classes", "parse"),
            initializer=False,
            expected_package="pkg",
            expected_owner_prefix=("domain", "owner"),
            expected_domain="domain",
            expected_first_role="helpers",
            expected_tail=("classes", "parse"),
        ),
        OwnershipClassificationTestCase(
            description="shared remains an ordinary owner segment rather than a role",
            module_parts=("pkg", "domain", "owner", "shared", "parse"),
            initializer=False,
            expected_package="pkg",
            expected_owner_prefix=("domain", "owner", "shared"),
            expected_domain="domain",
            expected_first_role=None,
            expected_tail=("parse",),
        ),
        OwnershipClassificationTestCase(
            description="no-role package initializer owns its complete package path",
            module_parts=("pkg", "domain", "owner"),
            initializer=True,
            expected_package="pkg",
            expected_owner_prefix=("domain", "owner"),
            expected_domain="domain",
            expected_first_role=None,
            expected_tail=(),
        ),
        OwnershipClassificationTestCase(
            description="no-role direct module is owned by its containing package",
            module_parts=("pkg", "domain", "owner", "internal"),
            initializer=False,
            expected_package="pkg",
            expected_owner_prefix=("domain", "owner"),
            expected_domain="domain",
            expected_first_role=None,
            expected_tail=("internal",),
        ),
        OwnershipClassificationTestCase(
            description="root initializer has package ownership without a domain",
            module_parts=("pkg",),
            initializer=True,
            expected_package="pkg",
            expected_owner_prefix=(),
            expected_domain=None,
            expected_first_role=None,
            expected_tail=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_module_path_when_classifying_then_preserves_structural_ownership(
    test_case: OwnershipClassificationTestCase,
) -> None:
    ownership: ModuleOwnership = classify_module_ownership(
        module_parts=test_case.module_parts, initializer=test_case.initializer
    )

    assert ownership.package == test_case.expected_package
    assert ownership.owner_prefix == test_case.expected_owner_prefix
    assert ownership.domain == test_case.expected_domain
    assert ownership.first_role == test_case.expected_first_role
    assert ownership.tail == test_case.expected_tail


@pytest.mark.parametrize(
    "test_case",
    [
        LayerRuleTestCase(
            "leaf owner may import its own helpers",
            "SFL101",
            (("src/pkg/config/main/load.py", "from pkg.config._helpers.parse import parse\n"),),
            (),
            (),
        ),
        LayerRuleTestCase(
            "branch owner grouped main may import its own helpers",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/commands/run.py",
                    "from pkg.domain.alpha._helpers.parse import parse\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "grouped helper buckets remain one owner",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/_helpers/read/one.py",
                    "from pkg.domain.alpha._helpers.write.two import write\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-owner main role package is public",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/_helpers/read.py",
                    "from pkg.domain.beta.main.commands import run\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-owner models role package is public",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.beta.models.core import Model\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "main may import classes in its own owner",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.alpha.classes.store import Store\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "first helpers role cannot be changed by a classes bucket",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.beta._helpers.classes.store import Store\n",
                ),
            ),
            ("SFL101",),
            (1,),
        ),
        LayerRuleTestCase(
            "metadata below first models role remains public",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.beta.models._helpers.schema import Model\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "nested shared path is not a public role",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from pkg.domain.beta.shared.parse import parse\n",
                ),
            ),
            ("SFL101",),
            (1,),
        ),
        LayerRuleTestCase(
            "cross-owner no-role direct module is internal",
            "SFL101",
            (("src/pkg/domain/alpha/main/run.py", "from pkg.domain.beta.internal import value\n"),),
            ("SFL101",),
            (1,),
        ),
        LayerRuleTestCase(
            "bare sibling owner import is internal",
            "SFL101",
            (
                ("src/pkg/domain/alpha/main/run.py", "import pkg.domain.beta\n"),
                ("src/pkg/domain/beta/__init__.py", ""),
            ),
            ("SFL101",),
            (1,),
        ),
        LayerRuleTestCase(
            "bare own package import retains the current owner",
            "SFL101",
            (
                ("src/pkg/domain/alpha/main/run.py", "import pkg.domain.alpha\n"),
                ("src/pkg/domain/alpha/__init__.py", ""),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "owner initializer may import its own helpers",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/__init__.py",
                    "from pkg.domain.alpha._helpers.parse import parse\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "role initializer retains the surrounding owner",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/__init__.py",
                    "from pkg.domain.alpha._helpers.parse import parse\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "resolvable relative import participates in ownership checks",
            "SFL101",
            (("src/pkg/domain/alpha/main/run.py", "from ...beta._helpers.parse import parse\n"),),
            ("SFL101",),
            (1,),
        ),
        LayerRuleTestCase(
            "same-owner relative import remains legal for the boundary rule",
            "SFL101",
            (("src/pkg/domain/alpha/main/run.py", "from .._helpers.parse import parse\n"),),
            (),
            (),
        ),
        LayerRuleTestCase(
            "ambiguous relative alias remains outside ownership inference",
            "SFL101",
            (("src/pkg/domain/alpha/main/run.py", "from . import local\n"),),
            (),
            (),
        ),
        LayerRuleTestCase(
            "grouped plain imports emit one fault per statement",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "import pkg.domain.beta._helpers.one, pkg.domain.gamma._helpers.two\n",
                ),
            ),
            ("SFL101",),
            (1,),
        ),
        LayerRuleTestCase(
            "different root package is ignored",
            "SFL101",
            (
                (
                    "src/pkg/domain/alpha/main/run.py",
                    "from other.domain.beta._helpers.parse import parse\n",
                ),
            ),
            (),
            (),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_same_domain_import_matrix_when_checking_then_enforces_owner_surfaces(
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
            "cross-domain main role is public",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta.main.entry import value\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-domain classes role is public",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta.classes.entry import value\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-domain models role is public",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta.models.entry import value\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-domain types role is public",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta.types.entry import value\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-domain constants role is public",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta.constants.entry import value\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-domain exceptions role is public",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta.exceptions.entry import value\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "cross-domain helpers role is internal",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta._helpers.parse import parse\n",
                ),
            ),
            ("SFL102",),
            (1,),
        ),
        LayerRuleTestCase(
            "cross-domain no-role module is internal",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from pkg.domain_b.beta.internal import value\n",
                ),
            ),
            ("SFL102",),
            (1,),
        ),
        LayerRuleTestCase(
            "cross-domain bare owner package is internal",
            "SFL102",
            (
                ("src/pkg/domain_a/alpha/main/run.py", "import pkg.domain_b.beta\n"),
                ("src/pkg/domain_b/beta/__init__.py", ""),
            ),
            ("SFL102",),
            (1,),
        ),
        LayerRuleTestCase(
            "top-level shared package is internal",
            "SFL102",
            (("src/pkg/domain_a/alpha/main/run.py", "from pkg.shared.parse import parse\n"),),
            ("SFL102",),
            (1,),
        ),
        LayerRuleTestCase(
            "cross-domain relative helper import is normalized",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from ....domain_b.beta._helpers.parse import parse\n",
                ),
            ),
            ("SFL102",),
            (1,),
        ),
        LayerRuleTestCase(
            "root initializer has no cross-domain ownership",
            "SFL102",
            (("src/pkg/__init__.py", "from pkg.domain_b.beta._helpers.parse import parse\n"),),
            (),
            (),
        ),
        LayerRuleTestCase(
            "external import is ignored",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "from external.domain_b.beta._helpers import parse\n",
                ),
            ),
            (),
            (),
        ),
        LayerRuleTestCase(
            "grouped plain cross-domain imports emit one fault per statement",
            "SFL102",
            (
                (
                    "src/pkg/domain_a/alpha/main/run.py",
                    "import pkg.domain_b.beta._helpers.one, pkg.domain_c.gamma._helpers.two\n",
                ),
            ),
            ("SFL102",),
            (1,),
        ),
        LayerRuleTestCase(
            "configured runtime package root preserves cross-domain ownership",
            "SFL102",
            (
                (
                    "python/acme/domain_a/alpha/main/run.py",
                    "from acme.domain_b.beta._helpers.parse import parse\n",
                ),
            ),
            ("SFL102",),
            (1,),
            roots=("python/acme",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_cross_domain_import_matrix_when_checking_then_enforces_public_roles(
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
        LayoutImportConsistencyTestCase(
            description="grouped helpers layout endorses bucket peer imports",
            role_code="SFR301",
            files=(
                (
                    "src/pkg/domain/alpha/_helpers/read/one.py",
                    "from pkg.domain.alpha._helpers.write.two import write\n",
                ),
                ("src/pkg/domain/alpha/_helpers/write/two.py", "def write() -> None:\n    pass\n"),
            ),
            expected_codes=(),
        ),
        LayoutImportConsistencyTestCase(
            description="grouped main layout endorses imports from its own helpers",
            role_code="SFR302",
            files=(
                (
                    "src/pkg/domain/alpha/main/commands/run.py",
                    "from pkg.domain.alpha._helpers.parse import parse\n",
                ),
                ("src/pkg/domain/alpha/_helpers/parse.py", "def parse() -> None:\n    pass\n"),
            ),
            expected_codes=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_endorsed_layout_when_checking_imports_then_same_owner_is_legal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: LayoutImportConsistencyTestCase,
) -> None:
    result: EvaluationResult = evaluate_layout_import_consistency(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
