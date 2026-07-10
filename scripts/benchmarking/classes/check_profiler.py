"""Instrument one in-process Strata check by phase and rule."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import cast

import strata.evaluation.core.main.evaluate as evaluate_module
from scripts.benchmarking.models import ProfileReport
from scripts.benchmarking.types import EvaluatorModule
from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import RepoRoot, ScopedFile
from strata.evaluation.core.main.evaluate import evaluate
from strata.evaluation.core.models import ParsedModule
from strata.reporting.core.main.render import render
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset


class CheckProfiler:
    """Collect phase and rule timings while preserving normal check behavior."""

    def __init__(self) -> None:
        """Initialize empty timing counters."""

        self._parse_seconds: float = 0.0
        self._rule_seconds: dict[str, float] = defaultdict(float)
        self._rule_calls: dict[str, int] = defaultdict(int)
        self._evaluator: EvaluatorModule = cast(EvaluatorModule, evaluate_module)
        self._original_parse: Callable[[ScopedFile], ParsedModule] = (
            self._evaluator.parse_scoped_file
        )
        self._original_execute: Callable[..., list[Fault]] = self._evaluator.execute_rule

    def run(self, project: Path) -> ProfileReport:
        """Run one instrumented check and restore evaluator functions afterward."""

        previous_directory: Path = Path.cwd()
        os.chdir(project)
        self._evaluator.parse_scoped_file = self._timed_parse
        self._evaluator.execute_rule = self._timed_execute
        try:
            return self._run_phases(project)
        finally:
            self._evaluator.parse_scoped_file = self._original_parse
            self._evaluator.execute_rule = self._original_execute
            os.chdir(previous_directory)

    def _timed_parse(self, scoped_file: ScopedFile) -> ParsedModule:
        started: float = time.perf_counter()
        result: ParsedModule = self._original_parse(scoped_file)
        self._parse_seconds += time.perf_counter() - started
        return result

    def _timed_execute(
        self,
        *,
        rule: RuleSpec,
        parsed_module: ParsedModule,
        config: Config,
        repo_root: RepoRoot,
    ) -> list[Fault]:
        started: float = time.perf_counter()
        result: list[Fault] = self._original_execute(
            rule=rule,
            parsed_module=parsed_module,
            config=config,
            repo_root=repo_root,
        )
        self._rule_seconds[rule.code] += time.perf_counter() - started
        self._rule_calls[rule.code] += 1
        return result

    def _run_phases(self, project: Path) -> ProfileReport:
        config, config_seconds = _timed(lambda: load_config(project))
        tree, discovery_seconds = _timed(lambda: discover_files(config))
        ruleset, catalogue_seconds = _timed(lambda: build_ruleset(config))
        result, evaluation_seconds = _timed(
            lambda: evaluate(tree=tree, ruleset=ruleset, config=config)
        )
        report, render_seconds = _timed(
            lambda: render(faults=result.faults, root=tree.repo_root.path, use_color=False)
        )
        rule_seconds: float = sum(self._rule_seconds.values())
        family_totals: dict[str, float] = defaultdict(float)
        for code, seconds in self._rule_seconds.items():
            family_totals[code[:3]] += seconds
        return ProfileReport(
            file_count=len(tree.files),
            fault_count=len(result.faults),
            rule_count=len(ruleset),
            config_seconds=config_seconds,
            discovery_seconds=discovery_seconds,
            catalogue_seconds=catalogue_seconds,
            evaluation_seconds=evaluation_seconds,
            parse_seconds=self._parse_seconds,
            rule_seconds=rule_seconds,
            engine_seconds=evaluation_seconds - self._parse_seconds - rule_seconds,
            render_seconds=render_seconds,
            rendered_bytes=len(report.text.encode("utf-8")),
            family_seconds=tuple(
                sorted(family_totals.items(), key=lambda item: item[1], reverse=True)
            ),
            rule_timings=tuple(
                (code, seconds, self._rule_calls[code])
                for code, seconds in sorted(
                    self._rule_seconds.items(), key=lambda item: item[1], reverse=True
                )
            ),
        )


def _timed[T](operation: Callable[[], T]) -> tuple[T, float]:
    started: float = time.perf_counter()
    result: T = operation()
    return result, time.perf_counter() - started
