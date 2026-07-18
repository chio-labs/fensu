"""Tests for native batch prewarming of evaluation parses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME

strata_facts: Any = pytest.importorskip(NATIVE_FACT_MODULE_NAME)

from strata.config.models import Config  # noqa: E402
from strata.discovery.models import DiscoveredTree, ScopedFile  # noqa: E402
from strata.evaluation._helpers import parsing as parsing_module  # noqa: E402
from strata.evaluation._helpers import project_analysis as project_analysis_module  # noqa: E402
from strata.evaluation._helpers.parsing import prewarm_scoped_files  # noqa: E402
from strata.evaluation._helpers.project_analysis import build_project_analysis  # noqa: E402
from strata.evaluation.exceptions import ParseError  # noqa: E402
from strata.evaluation.models import ParsedModule  # noqa: E402
from strata.evaluation.types import EvaluationProjectAnalysis  # noqa: E402
from tests.unit.src.strata.evaluation._test_types import (  # noqa: E402
    PrewarmFallbackTestCase,
    PrewarmFamilyPlanTestCase,
    PrewarmSeedTestCase,
)
from tests.unit.src.strata.evaluation.helpers import (  # noqa: E402
    discover_test_tree,
    write_scoped_source,
    write_sources,
)


@pytest.mark.parametrize(
    "test_case",
    [
        PrewarmSeedTestCase(
            description="prewarmed file is served without a second strict parse",
            source=b"value: int = 1\n",
            expected_reparse_calls=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_prewarmed_file_when_reading_parsed_module_then_skips_reparse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: PrewarmSeedTestCase,
) -> None:
    scoped_file: ScopedFile = write_scoped_source(tmp_path=tmp_path, source=test_case.source)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=discover_test_tree(config=config)
    )
    reparse_calls: list[ScopedFile] = []

    def record_reparse(*, scoped_file: ScopedFile, source_snapshot: object = None) -> ParsedModule:
        reparse_calls.append(scoped_file)
        raise AssertionError("prewarmed file was strict-parsed again")

    monkeypatch.setattr(project_analysis_module, "parse_scoped_file", record_reparse)
    prewarm_scoped_files(project=project, scoped_files=(scoped_file,))

    parsed: ParsedModule = project.parsed_module(scoped_file)
    assert len(reparse_calls) == test_case.expected_reparse_calls
    assert parsed.scoped_file.path == scoped_file.path
    assert parsed.source == test_case.source.decode()


@pytest.mark.parametrize(
    "test_case",
    [
        PrewarmFamilyPlanTestCase(
            description="prewarm extracts scope-planned fact families per file",
            files=(
                ("src/pkg/alpha/models.py", "VALUE: int = 1\n"),
                ("tests/unit/test_example.py", "VALUE: int = 2\n"),
            ),
            expected_family_plans=(
                (
                    "annotations",
                    "comments",
                    "contracts",
                    "control_flow",
                    "dataclasses",
                    "declarations",
                    "functions",
                    "hygiene",
                    "outer_state_mutations",
                    "parameter_mutations",
                    "references",
                ),
                (
                    "annotations",
                    "comments",
                    "control_flow",
                    "references",
                    "test_functions",
                    "test_module",
                ),
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_scopes_when_prewarming_then_plans_families_by_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: PrewarmFamilyPlanTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",), tests=("tests",))
    tree: DiscoveredTree = discover_test_tree(config=config)
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)
    captured: list[tuple[object, tuple[str, ...]]] = []

    def record_requests(*, requests: tuple[tuple[object, tuple[str, ...]], ...]) -> int:
        captured.extend(requests)
        return 0

    monkeypatch.setattr(parsing_module, "extract_native_fact_rows", record_requests)
    ordered_files: tuple[ScopedFile, ...] = tuple(
        sorted(tree.files, key=lambda scoped_file: str(scoped_file.path))
    )

    prewarm_scoped_files(project=project, scoped_files=ordered_files)

    assert tuple(families for _, families in captured) == test_case.expected_family_plans


@pytest.mark.parametrize(
    "test_case",
    [
        PrewarmFallbackTestCase(
            description="unparseable file is skipped and still fails through the strict path",
            source=b"value = (\n",
            expected_error_type=ParseError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unparseable_file_when_prewarming_then_strict_path_still_reports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: PrewarmFallbackTestCase,
) -> None:
    scoped_file: ScopedFile = write_scoped_source(tmp_path=tmp_path, source=test_case.source)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))
    project: EvaluationProjectAnalysis = build_project_analysis(
        tree=discover_test_tree(config=config)
    )

    prewarm_scoped_files(project=project, scoped_files=(scoped_file,))

    with pytest.raises(test_case.expected_error_type):
        _ = project.parsed_module(scoped_file)
