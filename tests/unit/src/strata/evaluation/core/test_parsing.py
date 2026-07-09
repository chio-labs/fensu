"""Tests for parsing diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import ScopedFile
from strata.evaluation.core.exceptions import ParseError
from strata.evaluation.core.helpers.parsing import parse_scoped_file
from tests.unit.src.strata.discovery.core.helpers import make_config
from tests.unit.src.strata.evaluation.core._test_types import ParseErrorTestCase
from tests.unit.src.strata.evaluation.core.helpers import write_sources


@pytest.mark.parametrize(
    "test_case",
    [
        ParseErrorTestCase(
            description="syntax error becomes clear parse error",
            source="def broken(:\n    pass\n",
            expected_error_fragment="Run strata under the target project's Python version or newer",
            expected_line=1,
            expected_column=12,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_python_when_parsing_then_raises_clear_parse_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ParseErrorTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=(("src/pkg/broken.py", test_case.source),))
    monkeypatch.chdir(tmp_path)
    scoped_file: ScopedFile = discover_files(make_config()).files[0]

    with pytest.raises(ParseError) as error:
        parse_scoped_file(scoped_file)

    assert test_case.expected_error_fragment in str(error.value)
    assert error.value.path == scoped_file.path
    assert error.value.line == test_case.expected_line
    assert error.value.column == test_case.expected_column
