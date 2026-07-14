"""Tests for the raw-AST-use classification of rule check functions."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleCheck
from strata.rules.catalog._helpers.module_use import check_uses_module
from strata.rules.catalog.constants import CORE_RULES
from strata.rules.catalog.main.build_ruleset import build_ruleset
from tests.unit.src.strata.rules.catalog.main._test_types import (
    CoreModuleFreedomTestCase,
    LoadedModuleUseTestCase,
    ModuleUseTestCase,
)
from tests.unit.src.strata.rules.catalog.main.helpers import (
    module_use_check,
    write_custom_rule_file,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ModuleUseTestCase(
            description="leading del module classifies as module-free",
            check_name="deletes-module",
            expected_uses_module=False,
        ),
        ModuleUseTestCase(
            description="reading a module attribute classifies as module-using",
            check_name="reads-module",
            expected_uses_module=True,
        ),
        ModuleUseTestCase(
            description="forwarding module to a helper classifies as module-using",
            check_name="forwards-module",
            expected_uses_module=True,
        ),
        ModuleUseTestCase(
            description="unavailable source conservatively classifies as module-using",
            check_name="no-source",
            expected_uses_module=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_check_shape_when_classifying_module_use_then_matches_expected(
    test_case: ModuleUseTestCase,
) -> None:
    check: RuleCheck = cast(RuleCheck, module_use_check(name=test_case.check_name))

    result: bool = check_uses_module(check=check)

    assert result == test_case.expected_uses_module


@pytest.mark.parametrize(
    "test_case",
    [
        CoreModuleFreedomTestCase(
            description="every core rule is provably raw-AST-free",
            expected_minimum_rules=100,
            expected_module_using_codes=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_core_catalogue_when_classifying_module_use_then_every_rule_is_module_free(
    test_case: CoreModuleFreedomTestCase,
) -> None:
    module_using: tuple[str, ...] = tuple(
        str(rule.code)
        for rule in filter(lambda rule: check_uses_module(check=rule.check), CORE_RULES)
    )

    assert len(CORE_RULES) >= test_case.expected_minimum_rules
    assert module_using == test_case.expected_module_using_codes


@pytest.mark.parametrize(
    "test_case",
    [
        LoadedModuleUseTestCase(
            description="loaded module-reading custom rule is flagged module-using",
            rule_code="XMU001",
            check_body="    return [ctx.fault(node=module.body[0])]",
            expected_uses_module=True,
        ),
        LoadedModuleUseTestCase(
            description="loaded module-free custom rule is flagged module-free",
            rule_code="XMU002",
            check_body="    del module\n    return []",
            expected_uses_module=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_loaded_custom_rule_when_building_ruleset_then_derives_module_use(
    tmp_path: Path,
    test_case: LoadedModuleUseTestCase,
) -> None:
    path: Path = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/custom_rule.py",
        rule_code=test_case.rule_code,
        check_body=test_case.check_body,
    )
    config: Config = Config(
        roots=("src/pkg",), rule_paths=(str(path),), select=(test_case.rule_code,)
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)

    assert ruleset[0].uses_module == test_case.expected_uses_module
