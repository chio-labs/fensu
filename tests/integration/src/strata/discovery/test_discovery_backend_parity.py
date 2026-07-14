"""Native and python discovery walks must classify identically."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

strata_facts: Any = pytest.importorskip("strata_facts")

from strata.config.models import Config  # noqa: E402
from strata.discovery.models import DiscoveredTree  # noqa: E402
from tests.integration.src.strata.discovery._test_types import (  # noqa: E402
    DiscoveryParityTestCase,
)
from tests.integration.src.strata.discovery.helpers import (  # noqa: E402
    discovered_with_backend,
    write_fixture_tree,
)


@pytest.mark.parametrize(
    "test_case",
    [
        DiscoveryParityTestCase(
            description="plain nested trees discover identically",
            files=(
                "src/pkg/domain/models.py",
                "src/pkg/domain/deep/logic.py",
                "tests/unit/test_logic.py",
                "scripts/tool.py",
            ),
            directory_symlinks=(),
            file_symlinks=(),
            expected_minimum_files=4,
        ),
        DiscoveryParityTestCase(
            description="hidden directories and dot names discover identically",
            files=(
                "src/pkg/.hidden/h.py",
                "src/pkg/.d.py",
                "src/pkg/dir.py/inner.py",
            ),
            directory_symlinks=(),
            file_symlinks=(),
            expected_minimum_files=3,
        ),
        DiscoveryParityTestCase(
            description="symlinked directories are not followed by either backend",
            files=(
                "src/pkg/real.py",
                "elsewhere/linked/hidden_target.py",
            ),
            directory_symlinks=(("src/pkg/linkdir", "elsewhere/linked"),),
            file_symlinks=(),
            expected_minimum_files=1,
        ),
        DiscoveryParityTestCase(
            description="symlinked files canonicalize identically inside the repo",
            files=(
                "src/pkg/real.py",
                "src/pkg/target_module.py",
            ),
            directory_symlinks=(),
            file_symlinks=(("src/pkg/alias.py", "src/pkg/target_module.py"),),
            expected_minimum_files=2,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_fixture_tree_when_discovering_with_both_backends_then_trees_match(
    test_case: DiscoveryParityTestCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_fixture_tree(
        root=tmp_path,
        files=test_case.files,
        directory_symlinks=test_case.directory_symlinks,
        file_symlinks=test_case.file_symlinks,
    )
    config: Config = Config(roots=("src/pkg",), tests=("tests",), tooling=("scripts",))

    python_tree: DiscoveredTree = discovered_with_backend(
        backend="python", repo_root=tmp_path, config=config, monkeypatch=monkeypatch
    )
    native_tree: DiscoveredTree = discovered_with_backend(
        backend="native", repo_root=tmp_path, config=config, monkeypatch=monkeypatch
    )

    assert native_tree.files == python_tree.files
    assert len(python_tree.files) >= test_case.expected_minimum_files
