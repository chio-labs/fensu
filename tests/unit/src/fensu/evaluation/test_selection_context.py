"""Tests that evaluation filtering retains complete project context."""

from pathlib import Path

import pytest

from fensu.config.models import Config, EvaluationConfig, RuleExceptionEntry
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.models import RuleSpec
from tests.unit.src.fensu.evaluation._test_types import EvaluationContextSelectionTestCase
from tests.unit.src.fensu.evaluation.helpers import (
    install_external_analysis_failure,
    layer_rule,
    selection_context_rule,
    write_sources,
)


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationContextSelectionTestCase(
            description="included importer observes excluded source structure and ownership",
            expected_codes=("XES001", "FFL102"),
            expected_context_message="CONTEXT: int = 1|context.py,parse.py",
            expected_evaluated_paths=("src/pkg/domain_a/core/main/run.py",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_excluded_context_when_evaluating_importer_then_retains_queries_and_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationContextSelectionTestCase,
) -> None:
    write_sources(
        repo_root=tmp_path,
        files=(
            (
                "src/pkg/domain_a/core/main/run.py",
                "from pkg.domain_b.core._helpers.parse import parse_value\n",
            ),
            ("src/pkg/domain_b/core/_helpers/context.py", "CONTEXT: int = 1\n"),
            ("src/pkg/domain_b/core/_helpers/parse.py", "def parse_value() -> None:\n    pass\n"),
        ),
    )
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        evaluation=EvaluationConfig(
            include=("src/pkg/domain_a/**",),
            exclude=("src/pkg/domain_b/**",),
        ),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="FFL102",
                path="src/pkg/domain_b/core/_helpers/parse.py",
                symbols=("parse_value",),
                reason="Excluded context receives no direct evaluation.",
            ),
        ),
    )
    tree: DiscoveredTree = discover_files(config=config)
    boundary_rule: RuleSpec = layer_rule(code="FFL102")
    install_external_analysis_failure(monkeypatch=monkeypatch)

    result: EvaluationResult = evaluate(
        tree=tree,
        ruleset=(selection_context_rule(), boundary_rule),
        config=config,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert result.faults[0].message == test_case.expected_context_message
    assert (
        tuple(
            evaluation.path.relative_to(tmp_path).as_posix()
            for evaluation in result.file_evaluations
        )
        == test_case.expected_evaluated_paths
    )
    assert tree.files[1].path.relative_to(tmp_path).as_posix().startswith("src/pkg/domain_b/")
