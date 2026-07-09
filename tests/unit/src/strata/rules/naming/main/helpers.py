"""Helpers for naming rule tests."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from strata.config.core.constants import DEFAULT_CONTRACTS
from strata.config.core.models import Config
from strata.discovery.core.main.discover_files import discover_files
from strata.evaluation.core.main.evaluate import evaluate
from strata.evaluation.core.models import EvaluationResult
from strata.rules.naming.constants import SFN_RULES
from tests.unit.src.strata.rules.naming.main._test_types import SfnRuleTestCase


def evaluate_naming_test_case(
    *, test_case: SfnRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate the naming rule family."""

    path: Path = tmp_path / "src" / "pkg" / "domain" / "core" / "helpers" / "checks.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    contracts: dict[str, str] = dict(DEFAULT_CONTRACTS)
    contracts.update(test_case.contracts)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",), tests=(), contracts=MappingProxyType(contracts))
    return evaluate(tree=discover_files(config), ruleset=SFN_RULES, config=config)
