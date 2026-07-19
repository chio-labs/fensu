"""Tests for native batch prewarming of evaluation parses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME

strata_facts: Any = pytest.importorskip(NATIVE_FACT_MODULE_NAME)

from strata.analysis.models import ProjectDependency  # noqa: E402
from strata.analysis.types import Analysis  # noqa: E402
from strata.config.models import Config  # noqa: E402
from strata.discovery.models import ScopedFile  # noqa: E402
from strata.evaluation._helpers import project_analysis as project_analysis_module  # noqa: E402
from strata.evaluation._helpers.parsing import prewarm_scoped_files  # noqa: E402
from strata.evaluation._helpers.project_analysis import build_project_analysis  # noqa: E402
from strata.evaluation.exceptions import ParseError  # noqa: E402
from strata.evaluation.models import ParsedModule  # noqa: E402
from strata.evaluation.types import EvaluationProjectAnalysis  # noqa: E402
from tests.unit.src.strata.evaluation._test_types import (  # noqa: E402
    PrewarmFallbackTestCase,
    PrewarmSeedTestCase,
)
from tests.unit.src.strata.evaluation.helpers import (  # noqa: E402
    discover_test_tree,
    write_scoped_source,
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

    analysis: Analysis | None = project.analysis(requester=scoped_file.path, path=scoped_file.path)
    parsed: ParsedModule = project.parsed_module(scoped_file)
    dependencies: tuple[ProjectDependency, ...] = project.dependencies_for(
        requester=scoped_file.path
    )

    assert len(reparse_calls) == test_case.expected_reparse_calls
    assert analysis is parsed.analysis
    assert parsed.scoped_file.path == scoped_file.path
    assert parsed.source == test_case.source.decode()
    assert dependencies[0].answer == parsed.source_fingerprint


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
