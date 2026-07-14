"""Tests for parsing diagnostics."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import pytest

from strata.analysis.constants import FACT_BACKEND_ENV_VARIABLE
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend, PythonSourceArtifact
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import ScopedFile
from strata.discovery.types import ScopeName
from strata.evaluation._helpers import parsing
from strata.evaluation._helpers.parsing import parse_scoped_file
from strata.evaluation.exceptions import ParseError
from strata.evaluation.models import ParsedModule
from tests.unit.src.strata.discovery.helpers import make_config
from tests.unit.src.strata.evaluation._test_types import (
    EncodedParseErrorTestCase,
    ParseDelegationTestCase,
    ParseErrorTestCase,
    SourceFingerprintTestCase,
)
from tests.unit.src.strata.evaluation.helpers import direct_ast_parse_paths, write_sources


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
    scoped_file: ScopedFile = discover_files(config=make_config()).files[0]

    with pytest.raises(ParseError) as error:
        parse_scoped_file(scoped_file=scoped_file)

    assert test_case.expected_error_fragment in str(error.value)
    assert error.value.path == scoped_file.path
    assert error.value.line == test_case.expected_line
    assert error.value.column == test_case.expected_column


@pytest.mark.parametrize(
    "test_case",
    [
        SourceFingerprintTestCase(
            description="raw bytes determine identity while newlines retain text semantics",
            source=b"value: int = 1\r\n",
            expected_source="value: int = 1\n",
            expected_fingerprint=hashlib.sha256(b"value: int = 1\r\n").hexdigest(),
        ),
        SourceFingerprintTestCase(
            description="UTF-8 BOM follows Python source decoding semantics",
            source=b"\xef\xbb\xbfvalue: int = 1\r\n",
            expected_source="value: int = 1\n",
            expected_fingerprint=hashlib.sha256(b"\xef\xbb\xbfvalue: int = 1\r\n").hexdigest(),
        ),
        SourceFingerprintTestCase(
            description="Latin-1 cookie follows Python source decoding semantics",
            source=b"# coding: latin-1\r\ncaf\xe9: int = 1\r\n",
            expected_source="# coding: latin-1\ncaf\u00e9: int = 1\n",
            expected_fingerprint=hashlib.sha256(
                b"# coding: latin-1\r\ncaf\xe9: int = 1\r\n"
            ).hexdigest(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_raw_source_bytes_when_parsing_then_preserves_exact_content_identity(
    tmp_path: Path,
    test_case: SourceFingerprintTestCase,
) -> None:
    path: Path = tmp_path / "src/pkg/models.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(test_case.source)
    scoped_file: ScopedFile = ScopedFile(
        path=path,
        root=tmp_path / "src/pkg",
        scope=ScopeName.ROOT,
        relative_parts=("models.py",),
    )

    parsed: ParsedModule = parse_scoped_file(scoped_file=scoped_file)

    assert parsed.source == test_case.expected_source
    assert parsed.source_fingerprint == test_case.expected_fingerprint


@pytest.mark.parametrize(
    "test_case",
    [
        ParseDelegationTestCase(
            description="evaluation delegates project source parsing to analysis",
            source=b"value: int = 1\n",
            expected_factory_calls=1,
            expected_direct_parse_paths=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_source_snapshot_when_evaluation_parses_then_delegates_to_analysis_factory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ParseDelegationTestCase,
) -> None:
    path: Path = tmp_path / "src/pkg/models.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(test_case.source)
    scoped_file: ScopedFile = ScopedFile(
        path=path,
        root=tmp_path / "src/pkg",
        scope=ScopeName.ROOT,
        relative_parts=("models.py",),
    )
    factory_calls: list[tuple[bytes, str | None]] = []
    original_factory: Callable[..., PythonSourceArtifact] = parsing.parse_python_source

    def observe_factory(
        *, path: Path, content: bytes, source_fingerprint: str | None = None
    ) -> PythonSourceArtifact:
        factory_calls.append((content, source_fingerprint))
        return original_factory(path=path, content=content, source_fingerprint=source_fingerprint)

    monkeypatch.setattr(parsing, "parse_python_source", observe_factory)
    monkeypatch.setenv(FACT_BACKEND_ENV_VARIABLE, FactBackend.PYTHON.value)
    select_fact_backend.cache_clear()

    _ = parsing.parse_scoped_file(scoped_file=scoped_file)
    select_fact_backend.cache_clear()
    direct_parse_paths: tuple[str, ...] = direct_ast_parse_paths(root=Path("src/strata/evaluation"))

    expected_call: tuple[bytes, str] = (
        test_case.source,
        hashlib.sha256(test_case.source).hexdigest(),
    )
    assert factory_calls == [expected_call] * test_case.expected_factory_calls
    assert direct_parse_paths == test_case.expected_direct_parse_paths


@pytest.mark.parametrize(
    "test_case",
    [
        EncodedParseErrorTestCase(
            description="invalid source bytes use the established evaluation parse diagnostic",
            source=b"value = '\xff'\n",
            expected_error_fragment="Run strata under the target project's Python version or newer",
            expected_line=None,
            expected_column=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_encoded_source_when_evaluation_parses_then_raises_parse_error(
    tmp_path: Path, test_case: EncodedParseErrorTestCase
) -> None:
    path: Path = tmp_path / "src/pkg/models.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(test_case.source)
    scoped_file: ScopedFile = ScopedFile(
        path=path,
        root=tmp_path / "src/pkg",
        scope=ScopeName.ROOT,
        relative_parts=("models.py",),
    )

    with pytest.raises(ParseError) as error:
        _ = parse_scoped_file(scoped_file=scoped_file)

    assert test_case.expected_error_fragment in str(error.value)
    assert error.value.line == test_case.expected_line
    assert error.value.column == test_case.expected_column
