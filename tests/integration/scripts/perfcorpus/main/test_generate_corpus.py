"""Behavior tests for deterministic corpus generation."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from fensu.cli.main.custom_check_host import run_custom_check as run_check
from scripts.perfcorpus.main.generate_corpus import generate_corpus
from scripts.perfcorpus.models import CorpusSpec, CorpusSummary
from tests.integration.scripts.perfcorpus.main._test_types import (
    CorpusDeterminismTestCase,
    CorpusFaultParityTestCase,
    CorpusShapeTestCase,
)
from tests.integration.scripts.perfcorpus.main.helpers import counted_files, tree_digest


@pytest.mark.parametrize(
    "test_case",
    [
        CorpusDeterminismTestCase(
            description="same seed produces byte-identical corpora",
            file_target=120,
            seed=7,
            expected_identical=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_one_seed_when_generating_twice_then_trees_are_byte_identical(
    tmp_path: Path,
    test_case: CorpusDeterminismTestCase,
) -> None:
    first_root: Path = tmp_path / "first"
    second_root: Path = tmp_path / "second"

    first_summary: CorpusSummary = generate_corpus(
        spec=CorpusSpec(target=first_root, file_target=test_case.file_target, seed=test_case.seed)
    )
    second_summary: CorpusSummary = generate_corpus(
        spec=CorpusSpec(target=second_root, file_target=test_case.file_target, seed=test_case.seed)
    )

    identical: bool = tree_digest(root=first_root) == tree_digest(root=second_root)
    assert identical is test_case.expected_identical
    assert first_summary == second_summary


@pytest.mark.parametrize(
    "test_case",
    [
        CorpusShapeTestCase(
            description="summary matches the written tree and config",
            file_target=120,
            seed=0,
            expected_minimum_domains=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_file_target_when_generating_then_summary_matches_written_tree(
    tmp_path: Path,
    test_case: CorpusShapeTestCase,
) -> None:
    summary: CorpusSummary = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )

    assert summary.domains >= test_case.expected_minimum_domains
    assert summary.files_written == counted_files(root=tmp_path)
    assert (tmp_path / "fensu.toml").is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        CorpusFaultParityTestCase(
            description="fensu reports exactly the declared injected faults",
            file_target=120,
            seed=0,
            expected_exit_code=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_generated_corpus_when_checking_then_faults_match_declared_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CorpusFaultParityTestCase,
) -> None:
    summary: CorpusSummary = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )
    monkeypatch.chdir(tmp_path)
    stdout: StringIO = StringIO()

    exit_code: int = run_check(argv=("--no-color", "--no-cache"), stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert f"Found {summary.faults_expected} faults" in stdout.getvalue()
