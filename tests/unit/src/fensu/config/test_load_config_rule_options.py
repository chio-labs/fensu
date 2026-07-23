"""Regression tests for public config loading with custom-rule options."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.config.exceptions import ConfigValidationError
from fensu.config.main.load_config import load_config
from fensu.config.models import Config
from tests.unit.src.fensu.config._test_types import (
    PublicRuleOptionsLoadTestCase,
    RuleOptionsValidationOrderTestCase,
)
from tests.unit.src.fensu.config.helpers import (
    write_custom_rule_file,
    write_fensu_toml,
)


@pytest.mark.parametrize(
    "test_case",
    [
        PublicRuleOptionsLoadTestCase(
            description="real typed custom rule override resolves through public loading",
            config_text=(
                'roots = ["src/pkg"]\ntests = []\ntooling = []\n'
                'rule_paths = ["rules/configured.py"]\n'
                "[rule_options.XCF001]\nlimit = 4\n"
            ),
            rule_relative_path="rules/configured.py",
            rule_source="""from __future__ import annotations

import ast

from fensu import Family, Fault, RuleContext, RuleOption, rule

_LIMIT = RuleOption.integer(name="limit", default=1, minimum=1, maximum=5)


@rule(
    code="XCF001",
    family=Family.CUSTOM,
    slug="configured-limit",
    message="configured limit",
    options=(_LIMIT,),
)
def configured_limit(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module, ctx
    return []
""",
            expected_rule_options={"XCF001": {"limit": 4}},
        )
    ],
    ids=lambda case: case.description,
)
def test_given_real_custom_rule_override_when_loading_config_then_returns_resolved_current_value(
    tmp_path: Path,
    test_case: PublicRuleOptionsLoadTestCase,
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path=test_case.rule_relative_path,
        contents=test_case.rule_source,
    )

    config: Config = load_config(tmp_path)

    assert config.rule_options == test_case.expected_rule_options


@pytest.mark.parametrize(
    "test_case",
    [
        RuleOptionsValidationOrderTestCase(
            description="malformed options fail before custom rule import side effect",
            config_text=(
                'roots = ["src/pkg"]\ntests = []\ntooling = []\n'
                'rule_paths = ["rules/side_effect.py"]\n'
                'rule_options = ["not-a-table"]\n'
            ),
            rule_relative_path="rules/side_effect.py",
            rule_source="""from pathlib import Path

Path(__file__).with_name("imported.marker").write_text("imported", encoding="utf-8")
""",
            marker_relative_path="rules/imported.marker",
            expected_error_type=ConfigValidationError,
            expected_error_fragment="rule_options must be a table",
            expected_marker_exists=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_malformed_rule_options_when_loading_then_rejects_before_custom_rule_import(
    tmp_path: Path,
    test_case: RuleOptionsValidationOrderTestCase,
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path=test_case.rule_relative_path,
        contents=test_case.rule_source,
    )
    marker_path: Path = tmp_path / test_case.marker_relative_path

    with pytest.raises(test_case.expected_error_type) as error:
        load_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)
    assert marker_path.exists() is test_case.expected_marker_exists
