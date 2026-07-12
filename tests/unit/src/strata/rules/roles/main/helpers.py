"""Helpers for roles rule tests."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from unittest.mock import Mock

import pytest

import strata.rules.roles.helpers.checks as role_checks
from strata.analysis.models import ProjectDependency
from strata.analysis.types import ProjectDependencyKind
from strata.config.constants import DEFAULT_THRESHOLDS
from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Threshold
from strata.rules.catalog.constants import CORE_RULES
from strata.rules.roles.constants import SFR_RULES
from tests.unit.src.strata.rules.roles.main._test_types import SfrRuleTestCase


def evaluate_role_test_case(
    *, test_case: SfrRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate a single roles rule."""

    scope_root: Path = tmp_path / ("scripts" if test_case.scope == "tooling" else "src/pkg")
    path: Path = scope_root / test_case.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    for support_file in test_case.support_files:
        support_path: Path = scope_root / support_file.relative_path
        if support_file.is_directory:
            support_path.mkdir(parents=True, exist_ok=True)
            continue
        support_path.parent.mkdir(parents=True, exist_ok=True)
        support_path.write_text(support_file.source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds.update(test_case.thresholds)
    runtime_root: Path = tmp_path / "src/pkg"
    runtime_root.mkdir(parents=True, exist_ok=True)
    tooling: tuple[str, ...] = ("scripts",) if test_case.scope == "tooling" else ()
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        tooling=tooling,
        thresholds=MappingProxyType(thresholds),
        threshold_overrides=test_case.threshold_overrides,
    )
    if test_case.rule_code == "SF":
        ruleset: tuple[RuleSpec, ...] = CORE_RULES
    elif test_case.rule_code == "SFR":
        ruleset = SFR_RULES
    else:
        ruleset = (_rule_by_code(test_case.rule_code),)
    return evaluate(
        tree=discover_files(config=config),
        ruleset=ruleset,
        config=config,
    )


def evaluate_flat_helpers_scale(
    *, project_root: Path, module_count: int, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Evaluate one namespace helpers role with the requested flat width."""

    helpers: Path = project_root / "src/pkg/domain/orders/helpers"
    helpers.mkdir(parents=True)
    for index in range(module_count):
        (helpers / f"module_{index:03d}.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(project_root)
    config: Config = Config(roots=("src/pkg",), tests=())
    return evaluate(
        tree=discover_files(config=config),
        ruleset=(_rule_by_code("SFR301"),),
        config=config,
    )


def evaluate_role_bucket_depth_scale(
    *, project_root: Path, depth: int, monkeypatch: pytest.MonkeyPatch
) -> tuple[EvaluationResult, int]:
    """Evaluate one namespace role bucket with Python initializers at each depth."""

    bucket: Path = project_root / "src/pkg/domain/orders/helpers/main"
    for index in range(depth):
        bucket /= f"level_{index:03d}"
        bucket.mkdir(parents=True)
        (bucket / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(project_root)
    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds[Threshold.MAX_ROLE_DEPTH] = depth + 1
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        thresholds=MappingProxyType(thresholds),
    )
    inspection_counter: Mock = Mock(wraps=role_checks._is_forbidden_role_bucket_name)
    with monkeypatch.context() as context:
        context.setattr(role_checks, "_is_forbidden_role_bucket_name", inspection_counter)
        result: EvaluationResult = evaluate(
            tree=discover_files(config=config),
            ruleset=(_rule_by_code("SFR301"),),
            config=config,
        )
    return result, inspection_counter.call_count


def anchor_dependencies(result: EvaluationResult) -> tuple[ProjectDependency, ...]:
    """Return compact Python-anchor observations from one evaluation."""

    return tuple(
        dependency
        for dependency in result.dependencies
        if dependency.kind is ProjectDependencyKind.PYTHON_ANCHOR
    )


def _rule_by_code(rule_code: str) -> RuleSpec:
    for rule in SFR_RULES:
        if rule.code == rule_code:
            return rule
    raise AssertionError(f"Unknown SFR rule code {rule_code}")
