"""Helpers for roles rule tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import MappingProxyType

import pytest

from fensu.analysis.models import ProjectDependency
from fensu.analysis.types import ProjectDependencyKind
from fensu.config.constants import DEFAULT_THRESHOLDS
from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Threshold
from fensu.rules.catalog.constants import CORE_RULES
from fensu.rules.roles.constants import FFR_RULES
from tests.unit.src.fensu.rules.roles.main._test_types import FfrRuleTestCase, FfrSupportFile


def _write_support_directory(*, path: Path, support_file: FfrSupportFile) -> None:
    del support_file
    path.mkdir(parents=True, exist_ok=True)


def _write_support_module(*, path: Path, support_file: FfrSupportFile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(support_file.source, encoding="utf-8")


def evaluate_role_test_case(
    *, test_case: FfrRuleTestCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Write a source file and evaluate a single roles rule."""

    scope_root: Path = tmp_path / {False: "src/pkg", True: "scripts"}[test_case.scope == "tooling"]
    path: Path = scope_root / test_case.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.source, encoding="utf-8")
    for support_file in test_case.support_files:
        support_path: Path = scope_root / support_file.relative_path
        writer: Callable[..., None] = {
            False: _write_support_module,
            True: _write_support_directory,
        }[support_file.is_directory]
        writer(path=support_path, support_file=support_file)
    monkeypatch.chdir(tmp_path)
    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds.update(test_case.thresholds)
    runtime_root: Path = tmp_path / "src/pkg"
    runtime_root.mkdir(parents=True, exist_ok=True)
    tooling: tuple[str, ...] = {False: (), True: ("scripts",)}[test_case.scope == "tooling"]
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        tooling=tooling,
        thresholds=MappingProxyType(thresholds),
        threshold_overrides=test_case.threshold_overrides,
    )
    rulesets_by_code: dict[str, tuple[RuleSpec, ...]] = {rule.code: (rule,) for rule in FFR_RULES}
    rulesets_by_code.update({"FF": CORE_RULES, "FFR": FFR_RULES})
    ruleset: tuple[RuleSpec, ...] = rulesets_by_code[test_case.rule_code]
    return evaluate(
        tree=discover_files(config=config),
        ruleset=ruleset,
        config=config,
    )


def evaluate_flat_helpers_scale(
    *, project_root: Path, module_count: int, monkeypatch: pytest.MonkeyPatch
) -> EvaluationResult:
    """Evaluate one namespace helpers role with the requested flat width."""

    helpers: Path = project_root / "src/pkg/domain/orders/_helpers"
    helpers.mkdir(parents=True)
    for index in range(module_count):
        (helpers / f"module_{index:03d}.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(project_root)
    config: Config = Config(roots=("src/pkg",), tests=())
    return evaluate(
        tree=discover_files(config=config),
        ruleset=(_rule_by_code("FFR301"),),
        config=config,
    )


def anchor_dependencies(result: EvaluationResult) -> tuple[ProjectDependency, ...]:
    """Return compact Python-anchor observations from one evaluation."""

    anchors: filter[ProjectDependency] = filter(
        lambda dependency: dependency.kind is ProjectDependencyKind.PYTHON_ANCHOR,
        result.dependencies,
    )
    return tuple(anchors)


def _rule_by_code(rule_code: str) -> RuleSpec:
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in FFR_RULES}
    return rules_by_code[rule_code]
