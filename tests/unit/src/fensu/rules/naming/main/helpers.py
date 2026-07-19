"""Helpers for naming rule tests."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from fensu.config.constants import DEFAULT_CONTRACTS
from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.naming.constants import FFN_RULES
from tests.unit.src.fensu.rules.naming.main._test_types import FfnRuleTestCase


def evaluate_naming_test_case(
    *, test_case: FfnRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate the naming rule family."""

    path: Path = tmp_path / "src" / "pkg" / "domain" / "core" / "_helpers" / "checks.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    contracts: dict[str, str] = dict(DEFAULT_CONTRACTS)
    contracts.update(test_case.contracts)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",), tests=(), contracts=MappingProxyType(contracts))
    return evaluate(tree=discover_files(config=config), ruleset=FFN_RULES, config=config)
