"""Helpers for tests rule tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.constants import CORE_RULES
from strata.rules.tests.constants import SFT_RULES
from tests.unit.src.strata.rules.tests.main._test_types import (
    SftConfiguredLayoutTestCase,
    SftRuleFile,
    SftRuleTestCase,
)

GOOD_TEST_TYPES_SOURCE: str = (
    "from dataclasses import dataclass\n\n"
    "@dataclass(frozen=True)\n"
    "class ExampleTestCase:\n"
    "    description: str\n"
    "    expected_value: int\n"
)
GOOD_TEST_SOURCE: str = (
    "import pytest\n\n"
    "from tests.unit.src.strata.rules.tests.main._test_types import ExampleTestCase\n\n"
    "@pytest.mark.parametrize(\n"
    '    "test_case",\n'
    '    [ExampleTestCase(description="example", expected_value=1)],\n'
    "    ids=lambda case: case.description,\n"
    ")\n"
    "def test_given_value_when_checking_then_matches_expected("
    "test_case: ExampleTestCase) -> None:\n"
    "    assert test_case.expected_value == 1\n"
)


def evaluate_tests_rule_test_case(
    *, test_case: SftRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source tree and evaluate one tests rule."""

    _write_file(tmp_path=tmp_path, relative_path="src/strata/__init__.py", source="")
    for runtime_path in test_case.runtime_paths:
        runtime_source: str = {
            False: "value: int = 1\n",
            True: "def run() -> None:\n    return None\n",
        }["/main/" in runtime_path]
        _write_file(tmp_path=tmp_path, relative_path=runtime_path, source=runtime_source)
    for tooling_path in test_case.tooling_paths:
        _write_file(tmp_path=tmp_path, relative_path=tooling_path, source="value: int = 1\n")
    for file in test_case.files:
        _write_file(tmp_path=tmp_path, relative_path=file.relative_path, source=file.source)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
    )
    rulesets_by_code: dict[str, tuple[RuleSpec, ...]] = {rule.code: (rule,) for rule in SFT_RULES}
    rulesets_by_code["SF"] = CORE_RULES
    selected_rules: list[RuleSpec] = []
    for code in test_case.rule_code.split(","):
        selected_rules.extend(rulesets_by_code[code])
    ruleset: tuple[RuleSpec, ...] = tuple(selected_rules)
    return evaluate(
        tree=discover_files(config=config),
        ruleset=ruleset,
        config=config,
    )


def evaluate_configured_layout_test_case(
    *,
    test_case: SftConfiguredLayoutTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> EvaluationResult:
    """Evaluate every test-layout rule for one configured path mirror."""

    for root in test_case.roots:
        (tmp_path / root).mkdir(parents=True, exist_ok=True)
    _write_file(tmp_path=tmp_path, relative_path=test_case.source_path, source="")
    _write_file(tmp_path=tmp_path, relative_path=test_case.test_path, source="")
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
    )
    layout_rules: tuple[RuleSpec, ...] = tuple(
        filter(lambda rule: "SFT001" <= rule.code <= "SFT008", SFT_RULES)
    )
    return evaluate(
        tree=discover_files(config=config),
        ruleset=layout_rules,
        config=config,
    )


def good_test_files(*, test_source: str = GOOD_TEST_SOURCE) -> tuple[SftRuleFile, ...]:
    """Return local _test_types.py plus a compliant test module."""

    return (
        SftRuleFile(
            description="local test case types",
            relative_path="tests/unit/src/strata/rules/tests/main/_test_types.py",
            source=GOOD_TEST_TYPES_SOURCE,
        ),
        SftRuleFile(
            description="test module",
            relative_path="tests/unit/src/strata/rules/tests/main/test_example.py",
            source=test_source,
        ),
    )


def _write_file(*, tmp_path: Path, relative_path: str, source: str) -> None:
    path: Path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
