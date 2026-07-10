"""Tests for routing discovered scopes to rule families."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.main.route import families_for_scope
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from strata.rules.authoring.types import Family
from tests.unit.src.strata.discovery.core._test_types import RoutingTestCase
from tests.unit.src.strata.discovery.core.helpers import make_config, only_file, write_python_files


@pytest.mark.parametrize(
    "test_case",
    [
        RoutingTestCase(
            description="root file routes to structural families",
            scope_path="src/pkg/domain/core/models.py",
            scope_name="root",
            expected_families=frozenset(
                {
                    Family.LAYERS,
                    Family.ROLES,
                    Family.SHAPE,
                    Family.NAMING,
                    Family.HYGIENE,
                    Family.ANNOTATIONS,
                }
            ),
        ),
        RoutingTestCase(
            description="test file routes to tests family",
            scope_path="tests/unit/test_models.py",
            scope_name="test",
            expected_families=frozenset({Family.ANNOTATIONS, Family.TESTS}),
        ),
        RoutingTestCase(
            description="tooling file routes to structural families",
            scope_path="scripts/check.py",
            scope_name="tooling",
            expected_families=frozenset(
                {
                    Family.LAYERS,
                    Family.ROLES,
                    Family.SHAPE,
                    Family.NAMING,
                    Family.HYGIENE,
                    Family.ANNOTATIONS,
                }
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_scoped_file_when_routing_then_returns_expected_families(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: RoutingTestCase,
) -> None:
    write_python_files(root=tmp_path, relative_paths=(test_case.scope_path,))
    (tmp_path / "src/pkg").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    tree: DiscoveredTree = discover_files(
        make_config(roots=("src/pkg",), tests=("tests",), tooling=("scripts",))
    )
    scoped_file: ScopedFile = only_file(files=tree.files)

    assert scoped_file.scope == test_case.scope_name
    assert families_for_scope(scoped_file=scoped_file) == test_case.expected_families
