"""Tests for the require-cacheable policy and hermetic custom-rule verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.core.exceptions import ConfigError
from strata.config.core.models import CacheConfig, Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.helpers.loading import (
    build_catalogue_from_config,
    build_ruleset_from_config,
)
from tests.unit.src.strata.rules.catalog.main._test_types import CacheableRuleValidationTestCase
from tests.unit.src.strata.rules.catalog.main.helpers import (
    rule_by_code,
    write_custom_rule_file,
)

_POLICY_CACHE: CacheConfig = CacheConfig(enabled=True, require_cacheable=True)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheableRuleValidationTestCase(
            description="require-cacheable policy promotes hermetic custom rules",
            prelude='import re\n\n_NAME_PATTERN: str = r"[a-z_]+"',
            check_body=(
                "    if ctx._project.exists(requester=ctx.path, path=ctx.repo_root / 'x.py'):\n"
                "        return []\n"
                "    return []"
            ),
            expected_error_fragment=None,
            expected_cacheable=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_require_cacheable_policy_when_building_catalogue_then_promotes_custom_rules(
    tmp_path: Path,
    test_case: CacheableRuleValidationTestCase,
) -> None:
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/custom.py",
        rule_code="XCH001",
        prelude=test_case.prelude,
        check_body=test_case.check_body,
    )
    config: Config = Config(
        roots=(),
        rule_paths=("rules",),
        select=("SF", "X"),
        cache=_POLICY_CACHE,
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset_from_config(config=config, repo_root=tmp_path)

    loaded: RuleSpec = rule_by_code(rules=ruleset, code="XCH001")
    assert loaded.cacheable is test_case.expected_cacheable


@pytest.mark.parametrize(
    "test_case",
    [
        CacheableRuleValidationTestCase(
            description="policy rejects rules importing side-effect modules",
            prelude="import os",
            check_body="    return []",
            expected_error_fragment="imports os",
            expected_cacheable=False,
        ),
        CacheableRuleValidationTestCase(
            description="policy rejects rules importing the project package",
            prelude="from myapp.constants import LIMIT",
            check_body="    return []",
            expected_error_fragment="imports myapp.constants",
            expected_cacheable=False,
        ),
        CacheableRuleValidationTestCase(
            description="policy rejects rules reading files outside the facade",
            prelude="",
            check_body="    _ = ctx.path.read_text()\n    return []",
            expected_error_fragment="untracked operation read_text",
            expected_cacheable=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_require_cacheable_policy_when_rule_is_unhermetic_then_raises_config_error(
    tmp_path: Path,
    test_case: CacheableRuleValidationTestCase,
) -> None:
    (tmp_path / "myapp").mkdir()
    (tmp_path / "myapp/__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (tmp_path / "myapp/constants.py").write_text("LIMIT: int = 3\n", encoding="utf-8")
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/custom.py",
        rule_code="XCH002",
        prelude=test_case.prelude,
        check_body=test_case.check_body,
    )
    config: Config = Config(
        roots=(),
        rule_paths=("rules",),
        select=("SF", "X"),
        cache=_POLICY_CACHE,
    )

    with pytest.raises(ConfigError, match=str(test_case.expected_error_fragment)):
        build_ruleset_from_config(config=config, repo_root=tmp_path)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheableRuleValidationTestCase(
            description="without the policy custom rules load unscanned and uncacheable",
            prelude="import os",
            check_body="    return []",
            expected_error_fragment=None,
            expected_cacheable=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_policy_when_building_catalogue_then_skips_scan(
    tmp_path: Path,
    test_case: CacheableRuleValidationTestCase,
) -> None:
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/custom.py",
        rule_code="XCH003",
        prelude=test_case.prelude,
    )
    config: Config = Config(roots=(), rule_paths=("rules",))

    catalogue: tuple[RuleSpec, ...] = build_catalogue_from_config(config=config, repo_root=tmp_path)

    loaded: RuleSpec = rule_by_code(rules=catalogue, code="XCH003")
    assert loaded.cacheable is test_case.expected_cacheable


@pytest.mark.parametrize(
    "test_case",
    [
        CacheableRuleValidationTestCase(
            description="policy ignores unhermetic custom rules that are not selected",
            prelude="import os",
            check_body="    return []",
            expected_error_fragment=None,
            expected_cacheable=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unselected_unhermetic_rule_when_building_ruleset_then_skips_scan(
    tmp_path: Path,
    test_case: CacheableRuleValidationTestCase,
) -> None:
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/custom.py",
        rule_code="XCH006",
        prelude=test_case.prelude,
    )
    config: Config = Config(roots=(), rule_paths=("rules",), cache=_POLICY_CACHE)

    ruleset: tuple[RuleSpec, ...] = build_ruleset_from_config(config=config, repo_root=tmp_path)

    selected_codes: tuple[str, ...] = tuple(rule.code for rule in ruleset)
    assert ("XCH006" in selected_codes) is test_case.expected_cacheable
