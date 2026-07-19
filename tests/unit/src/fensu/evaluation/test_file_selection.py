"""Tests for direct evaluation target selection."""

from pathlib import Path

import pytest

from fensu.config.exceptions import ConfigError
from fensu.config.models import Config, EvaluationConfig
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree, ScopedFile
from fensu.evaluation.main.select_files import select_evaluation_files
from fensu.evaluation.models import EvaluationSelection
from tests.unit.src.fensu.evaluation._test_types import (
    EvaluationSelectionErrorTestCase,
    EvaluationSelectionTestCase,
)
from tests.unit.src.fensu.evaluation.helpers import write_sources


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationSelectionTestCase(
            description="no filters select every discovered scope",
            include=(),
            exclude=(),
            expected_paths=(
                "scripts/tool.py",
                "src/pkg/a.py",
                "src/pkg/legacy.py",
                "tests/test_a.py",
            ),
            expected_filtered=False,
        ),
        EvaluationSelectionTestCase(
            description="include patterns select their union across scopes",
            include=("src/pkg/a.py", "tests/**"),
            exclude=(),
            expected_paths=("src/pkg/a.py", "tests/test_a.py"),
            expected_filtered=True,
        ),
        EvaluationSelectionTestCase(
            description="exclude-only patterns subtract matching paths",
            include=(),
            exclude=("**/legacy.py",),
            expected_paths=("scripts/tool.py", "src/pkg/a.py", "tests/test_a.py"),
            expected_filtered=True,
        ),
        EvaluationSelectionTestCase(
            description="exclude wins over an included path",
            include=("src/pkg/**",),
            exclude=("src/pkg/legacy.py",),
            expected_paths=("src/pkg/a.py",),
            expected_filtered=True,
        ),
        EvaluationSelectionTestCase(
            description="unmatched excludes are legal",
            include=("scripts/**",),
            exclude=("**/generated/**",),
            expected_paths=("scripts/tool.py",),
            expected_filtered=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_discovered_tree_when_selecting_evaluation_files_then_returns_expected_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationSelectionTestCase,
) -> None:
    write_sources(
        repo_root=tmp_path,
        files=(
            ("src/pkg/a.py", ""),
            ("src/pkg/legacy.py", ""),
            ("tests/test_a.py", ""),
            ("scripts/tool.py", ""),
        ),
    )
    monkeypatch.chdir(tmp_path)
    tree: DiscoveredTree = discover_files(
        config=Config(roots=("src/pkg",), tests=("tests",), tooling=("scripts",))
    )
    original_files: tuple[ScopedFile, ...] = tree.files

    selection: EvaluationSelection = select_evaluation_files(
        tree=tree,
        config=EvaluationConfig(include=test_case.include, exclude=test_case.exclude),
    )

    assert tuple(path.path.relative_to(tmp_path).as_posix() for path in selection.files) == (
        test_case.expected_paths
    )
    assert selection.filtered is test_case.expected_filtered
    assert selection.discovered_count == len(original_files)
    assert selection.excluded_count == len(original_files) - len(test_case.expected_paths)
    assert tree.files is original_files


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationSelectionErrorTestCase(
            description="stale include pattern fails by name",
            include=("src/pkg/missing.py",),
            exclude=(),
            expected_error_fragment="matched no discovered Python files: src/pkg/missing.py",
        ),
        EvaluationSelectionErrorTestCase(
            description="exclusions removing every included file fail",
            include=("src/pkg/**",),
            exclude=("src/pkg/**",),
            expected_error_fragment="selects zero Python files",
        ),
        EvaluationSelectionErrorTestCase(
            description="exclude-only empty target fails",
            include=(),
            exclude=("**",),
            expected_error_fragment="selects zero Python files",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_effective_selection_when_selecting_then_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationSelectionErrorTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=(("src/pkg/a.py", ""),))
    monkeypatch.chdir(tmp_path)
    tree: DiscoveredTree = discover_files(config=Config(roots=("src/pkg",), tests=()))

    with pytest.raises(ConfigError) as error:
        select_evaluation_files(
            tree=tree,
            config=EvaluationConfig(include=test_case.include, exclude=test_case.exclude),
        )

    assert test_case.expected_error_fragment in str(error.value)
