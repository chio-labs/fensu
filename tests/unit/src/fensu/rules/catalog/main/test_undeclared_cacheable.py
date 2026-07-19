"""Tests for the undeclared appears-cacheable probe."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.config.models import Config
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog._helpers.loading import build_ruleset_from_config
from fensu.rules.catalog.main.undeclared_cacheable import undeclared_cacheable_codes
from tests.unit.src.fensu.rules.catalog.main._test_types import UndeclaredCacheableTestCase
from tests.unit.src.fensu.rules.catalog.main.helpers import write_custom_rule_file


@pytest.mark.parametrize(
    "test_case",
    [
        UndeclaredCacheableTestCase(
            description="undeclared hermetic rule is reported as appearing cacheable",
            decorator_arguments="",
            prelude="import re",
            expected_codes=("XUC001",),
        ),
        UndeclaredCacheableTestCase(
            description="undeclared unhermetic rule is not reported",
            decorator_arguments="",
            prelude="import os",
            expected_codes=(),
        ),
        UndeclaredCacheableTestCase(
            description="declared promise is not reported again",
            decorator_arguments=", cacheable=True",
            prelude="import re",
            expected_codes=(),
        ),
        UndeclaredCacheableTestCase(
            description="declared opt-out silences the report",
            decorator_arguments=", cacheable=False",
            prelude="import re",
            expected_codes=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_when_probing_then_reports_undeclared_hermetic_codes(
    tmp_path: Path,
    test_case: UndeclaredCacheableTestCase,
) -> None:
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/custom.py",
        rule_code="XUC001",
        prelude=test_case.prelude,
        decorator_arguments=test_case.decorator_arguments,
    )
    config: Config = Config(roots=(), rule_paths=("rules",), select=("FF", "X"))
    ruleset: tuple[RuleSpec, ...] = build_ruleset_from_config(config=config, repo_root=tmp_path)

    codes: tuple[str, ...] = undeclared_cacheable_codes(
        rules=ruleset,
        allowed_packages=frozenset(),
    )

    assert codes == test_case.expected_codes
