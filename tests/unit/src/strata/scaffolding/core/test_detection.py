"""Tests for deterministic repository layout detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.scaffolding.core.exceptions import PyprojectParseError, RepositoryDetectionError
from strata.scaffolding.core.main.detect_repository_layout import detect_repository_layout
from strata.scaffolding.core.models import DetectedRepositoryLayout
from tests.unit.src.strata.scaffolding.core._test_types import (
    DetectionErrorTestCase,
    DetectionTestCase,
    MetadataMarkerSymlinkTestCase,
)
from tests.unit.src.strata.scaffolding.core.helpers import (
    build_detection_repository,
    build_repository,
    candidate_details,
    candidate_test_details,
    prepare_metadata_marker_symlink,
)


@pytest.mark.parametrize(
    "test_case",
    [
        DetectionTestCase(
            description="hatch metadata outranks duplicate project and filesystem signals",
            files=(
                (
                    "pyproject.toml",
                    '[project]\nname = "acme"\n[tool.hatch.build.targets.wheel]\npackages = ["src/acme"]\n[tool.ruff]\nsrc = ["src"]\n',
                ),
                ("src/acme/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("src/acme", "pyproject: hatch packages"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="setuptools find and package-dir preserve declaration precedence",
            files=(
                (
                    "pyproject.toml",
                    '[tool.setuptools.packages.find]\nwhere = ["src"]\n[tool.setuptools.package-dir]\nlegacy = "lib/legacy"\n',
                ),
                ("src/alpha/__init__.py", ""),
                ("src/zeta/__init__.py", ""),
                ("lib/legacy/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(
                ("src/alpha", "pyproject: setuptools find.where"),
                ("src/zeta", "pyproject: setuptools find.where"),
                ("lib/legacy", "pyproject: setuptools package-dir"),
            ),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(3, 3, False),
        ),
        DetectionTestCase(
            description="setuptools empty package-dir expands immediate packages",
            files=(
                ("pyproject.toml", '[tool.setuptools.package-dir]\n"" = "python"\n'),
                ("python/acme/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("python/acme", "pyproject: setuptools package-dir"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="poetry package include and source locate runtime package",
            files=(
                ("pyproject.toml", '[[tool.poetry.packages]]\ninclude = "acme"\nfrom = "lib"\n'),
                ("lib/acme/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("lib/acme", "pyproject: poetry packages"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="flit dotted module name resolves beneath source container",
            files=(
                ("pyproject.toml", '[tool.flit.module]\nname = "acme.api"\n'),
                ("src/acme/api/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("src/acme/api", "pyproject: flit module name"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="one-level uv workspace expands sorted members and nested metadata",
            files=(
                ("pyproject.toml", '[tool.uv.workspace]\nmembers = ["packages/*"]\n'),
                ("packages/beta/pyproject.toml", '[project]\nname = "beta-lib"\n'),
                ("packages/beta/src/beta_lib/__init__.py", ""),
                ("packages/alpha/src/alpha/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(
                ("packages/alpha/src/alpha", "pyproject: uv workspace member"),
                ("packages/beta/src/beta_lib", "pyproject: uv workspace member"),
            ),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(2, 2, False),
        ),
        DetectionTestCase(
            description="normalized project name matches packages member source",
            files=(
                ("pyproject.toml", '[project]\nname = "My.Cool-Pkg"\n'),
                ("packages/member/src/my_cool_pkg/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("packages/member/src/my_cool_pkg", "pyproject: project name"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="ruff source discovers package children in sorted order",
            files=(
                ("pyproject.toml", '[tool.ruff]\nsrc = ["lib"]\n'),
                ("lib/b/__init__.py", ""),
                ("lib/a/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("lib/a", "ruff src"), ("lib/b", "ruff src")),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(2, 2, False),
        ),
        DetectionTestCase(
            description="pytest paths precede tests and test filesystem candidates",
            files=(
                ("pyproject.toml", '[tool.pytest.ini_options]\ntestpaths = ["spec", "tests"]\n'),
                ("src/pkg/__init__.py", ""),
            ),
            directories=("spec", "tests", "test"),
            expected_roots=(("src/pkg", "directory scan"),),
            expected_tests=(
                ("spec", "pytest testpaths", True),
                ("tests", "pytest testpaths", True),
                ("test", "directory scan", True),
            ),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="filesystem scans root and containers while excluding decoys",
            files=(
                ("flat/__init__.py", ""),
                ("libs/shared/__init__.py", ""),
                ("tests/fake/__init__.py", ""),
                ("docs/sample/__init__.py", ""),
                (".venv/ghost/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("flat", "directory scan"), ("libs/shared", "directory scan")),
            expected_tests=(("tests", "directory scan", True),),
            expected_tooling=(),
            expected_python_state=(2, 2, False),
        ),
        DetectionTestCase(
            description="tests is preferred to test and tooling requires Python",
            files=(
                ("src/pkg/__init__.py", ""),
                ("scripts/run.py", "x = 1\n"),
                ("tools/build.sh", "#!/bin/sh\n"),
            ),
            directories=("test", "tests"),
            expected_roots=(("src/pkg", "directory scan"),),
            expected_tests=(("tests", "directory scan", True), ("test", "directory scan", True)),
            expected_tooling=("scripts",),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="ordinary gitignore name excludes fallback packages at every depth",
            files=(
                (".gitignore", "ignored\n"),
                ("ignored/__init__.py", ""),
                ("src/ignored/__init__.py", ""),
                ("src/kept/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("src/kept", "directory scan"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="anchored gitignore directory excludes only repository-root package",
            files=(
                (".gitignore", "/rootpkg/\n"),
                ("rootpkg/__init__.py", ""),
                ("src/rootpkg/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("src/rootpkg", "directory scan"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="directory-only gitignore rule excludes package and all Python state",
            files=(
                (".gitignore", "generated/\n"),
                ("generated/__init__.py", ""),
                ("generated/module.py", ""),
                ("src/kept/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("src/kept", "directory scan"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="gitignore glob excludes matching fallback package",
            files=(
                (".gitignore", "src/*_generated/\n"),
                ("src/api_generated/__init__.py", ""),
                ("src/api_generated/module.py", ""),
                ("src/api/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("src/api", "directory scan"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="later gitignore negation restores fallback package and Python state",
            files=(
                (".gitignore", "src/*\n!src/keep\n!src/keep/__init__.py\n"),
                ("src/drop/__init__.py", ""),
                ("src/keep/__init__.py", ""),
            ),
            directories=(),
            expected_roots=(("src/keep", "directory scan"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="single-segment gitignore star does not match nested Python path",
            files=(
                (".gitignore", "src/*.py\n"),
                ("pkg/__init__.py", ""),
                ("src/top.py", ""),
                ("src/nested/module.py", ""),
            ),
            directories=(),
            expected_roots=(("pkg", "directory scan"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(2, 1, False),
        ),
        DetectionTestCase(
            description="gitignore globstar matches nested Python path",
            files=(
                (".gitignore", "src/**/*.py\n"),
                ("pkg/__init__.py", ""),
                ("src/top.py", ""),
                ("src/nested/module.py", ""),
            ),
            directories=(),
            expected_roots=(("pkg", "directory scan"),),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 1, False),
        ),
        DetectionTestCase(
            description="loose Python is package-empty without inventing roots",
            files=(("app.py", "x = 1\n"),),
            directories=(),
            expected_roots=(),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(1, 0, True),
        ),
        DetectionTestCase(
            description="fully empty repository gets only absent tests default",
            files=(),
            directories=(),
            expected_roots=(),
            expected_tests=(("tests", "not present yet", False),),
            expected_tooling=(),
            expected_python_state=(0, 0, True),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_repository_signals_when_detecting_layout_then_returns_ranked_candidates(
    test_case: DetectionTestCase, tmp_path: Path
) -> None:
    build_detection_repository(root=tmp_path, test_case=test_case)

    detected: DetectedRepositoryLayout = detect_repository_layout(repository=tmp_path)

    assert candidate_details(candidates=detected.roots) == test_case.expected_roots
    assert candidate_test_details(candidates=detected.tests) == test_case.expected_tests
    assert tuple(candidate.path for candidate in detected.tooling) == test_case.expected_tooling
    assert (
        detected.python.file_count,
        detected.python.package_count,
        detected.python.is_empty,
    ) == test_case.expected_python_state


@pytest.mark.parametrize(
    "test_case",
    [
        DetectionErrorTestCase(
            description="malformed root pyproject is reported with its filename",
            pyproject_text="[project\nname = 'broken'",
            expected_error_type=PyprojectParseError,
            expected_error_fragment="Could not parse pyproject.toml",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_malformed_pyproject_when_detecting_layout_then_raises_parse_error(
    test_case: DetectionErrorTestCase, tmp_path: Path
) -> None:
    build_repository(root=tmp_path, files=(("pyproject.toml", test_case.pyproject_text),))

    with pytest.raises(test_case.expected_error_type) as error:
        detect_repository_layout(repository=tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        MetadataMarkerSymlinkTestCase(
            description="metadata-selected package symlink marker is rejected",
            pyproject_text='[tool.hatch.build.targets.wheel]\npackages = ["src/pkg"]\n',
            marker_path="src/pkg/__init__.py",
            expected_error_type=RepositoryDetectionError,
            expected_error_fragment="Detected package marker must not be a symlink",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_metadata_package_with_symlink_marker_when_detecting_then_raises_error(
    test_case: MetadataMarkerSymlinkTestCase, tmp_path: Path
) -> None:
    build_repository(root=tmp_path, files=(("pyproject.toml", test_case.pyproject_text),))
    prepare_metadata_marker_symlink(root=tmp_path, marker_path=test_case.marker_path)

    with pytest.raises(test_case.expected_error_type) as error:
        detect_repository_layout(repository=tmp_path)

    assert test_case.expected_error_fragment in str(error.value)
