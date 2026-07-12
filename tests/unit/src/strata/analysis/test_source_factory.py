"""Tests for exact Python source analysis construction."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.main import parse_source
from strata.analysis.types import PythonSourceArtifact
from tests.unit.src.strata.analysis._test_types import (
    PythonSourceFactoryErrorTestCase,
    PythonSourceFactoryOperationTestCase,
    PythonSourceFactoryTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        PythonSourceFactoryTestCase(
            description="LF source remains LF",
            content=b"value = 1\nother = 2\n",
            expected_source="value = 1\nother = 2\n",
            expected_fingerprint=hashlib.sha256(b"value = 1\nother = 2\n").hexdigest(),
            expected_assignment_count=2,
        ),
        PythonSourceFactoryTestCase(
            description="CRLF source normalizes to LF",
            content=b"value = 1\r\nother = 2\r\n",
            expected_source="value = 1\nother = 2\n",
            expected_fingerprint=hashlib.sha256(b"value = 1\r\nother = 2\r\n").hexdigest(),
            expected_assignment_count=2,
        ),
        PythonSourceFactoryTestCase(
            description="CR source normalizes to LF",
            content=b"value = 1\rother = 2\r",
            expected_source="value = 1\nother = 2\n",
            expected_fingerprint=hashlib.sha256(b"value = 1\rother = 2\r").hexdigest(),
            expected_assignment_count=2,
        ),
        PythonSourceFactoryTestCase(
            description="UTF-8 source preserves non-ASCII text",
            content="caf\u00e9 = 'na\u00efve'\n".encode(),
            expected_source="caf\u00e9 = 'na\u00efve'\n",
            expected_fingerprint=hashlib.sha256("caf\u00e9 = 'na\u00efve'\n".encode()).hexdigest(),
            expected_assignment_count=1,
        ),
        PythonSourceFactoryTestCase(
            description="UTF-8 BOM is decoded with Python source semantics",
            content=b"\xef\xbb\xbfvalue = 1\r\n",
            expected_source="value = 1\n",
            expected_fingerprint=hashlib.sha256(b"\xef\xbb\xbfvalue = 1\r\n").hexdigest(),
            expected_assignment_count=1,
        ),
        PythonSourceFactoryTestCase(
            description="PEP 263 Latin-1 cookie controls source decoding",
            content=b"# coding: latin-1\r\ncaf\xe9 = 1\r\n",
            expected_source="# coding: latin-1\ncaf\u00e9 = 1\n",
            expected_fingerprint=hashlib.sha256(
                b"# coding: latin-1\r\ncaf\xe9 = 1\r\n"
            ).hexdigest(),
            expected_assignment_count=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_exact_bytes_when_parsing_python_source_then_builds_normalized_artifact(
    test_case: PythonSourceFactoryTestCase,
) -> None:
    path: Path = Path("src/pkg/module.py")

    artifact: PythonSourceArtifact = parse_source.parse_python_source(
        path=path, content=test_case.content
    )

    assert artifact.path == path
    assert artifact.source == test_case.expected_source
    assert artifact.source_fingerprint == test_case.expected_fingerprint
    assert len(artifact.module.body) == test_case.expected_assignment_count
    assert isinstance(artifact.module, ast.Module)


@pytest.mark.parametrize(
    "test_case",
    [
        PythonSourceFactoryErrorTestCase(
            description="invalid UTF-8 becomes structured source parse failure",
            content=b"value = '\xff'\n",
            expected_error_type=PythonSourceParseError,
            expected_message="invalid or missing encoding declaration",
            expected_line=None,
            expected_column=None,
        ),
        PythonSourceFactoryErrorTestCase(
            description="unknown encoding cookie becomes structured source parse failure",
            content=b"# coding: not-a-codec\nvalue = 1\n",
            expected_error_type=PythonSourceParseError,
            expected_message="unknown encoding: not-a-codec",
            expected_line=None,
            expected_column=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_encoding_when_parsing_python_source_then_raises_structured_error(
    test_case: PythonSourceFactoryErrorTestCase,
) -> None:
    with pytest.raises(PythonSourceParseError) as error:
        parse_source.parse_python_source(path=Path("invalid.py"), content=test_case.content)

    assert isinstance(error.value, test_case.expected_error_type)
    assert error.value.message == test_case.expected_message
    assert error.value.line == test_case.expected_line
    assert error.value.column == test_case.expected_column


@pytest.mark.parametrize(
    "test_case",
    [
        PythonSourceFactoryErrorTestCase(
            description="invalid syntax exposes original parser fields",
            content=b"def broken(:\n    pass\n",
            expected_error_type=PythonSourceParseError,
            expected_message="invalid syntax",
            expected_line=1,
            expected_column=12,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_syntax_when_parsing_python_source_then_raises_structured_error(
    test_case: PythonSourceFactoryErrorTestCase,
) -> None:
    path: Path = Path("broken.py")

    with pytest.raises(PythonSourceParseError) as error:
        parse_source.parse_python_source(path=path, content=test_case.content)

    assert isinstance(error.value, test_case.expected_error_type)
    assert error.value.path == path
    assert error.value.message == test_case.expected_message
    assert error.value.line == test_case.expected_line
    assert error.value.column == test_case.expected_column


@pytest.mark.parametrize(
    "test_case",
    [
        PythonSourceFactoryOperationTestCase(
            description="direct factory call parses and hashes exactly once",
            content=b"value = 1\n",
            source_fingerprint=None,
            expected_fingerprint=hashlib.sha256(b"value = 1\n").hexdigest(),
            expected_parse_count=1,
            expected_hash_count=1,
        ),
        PythonSourceFactoryOperationTestCase(
            description="trusted snapshot fingerprint avoids duplicate hashing",
            content=b"value = 1\n",
            source_fingerprint="a" * 64,
            expected_fingerprint="a" * 64,
            expected_parse_count=1,
            expected_hash_count=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_valid_source_when_parsing_artifact_then_uses_expected_operations(
    monkeypatch: pytest.MonkeyPatch,
    test_case: PythonSourceFactoryOperationTestCase,
) -> None:
    parse_spy: Mock = Mock(wraps=ast.parse)
    hash_spy: Mock = Mock(wraps=hashlib.sha256)
    monkeypatch.setattr(parse_source.ast, "parse", parse_spy)
    monkeypatch.setattr(parse_source.hashlib, "sha256", hash_spy)

    artifact: PythonSourceArtifact = parse_source.parse_python_source(
        path=Path("module.py"),
        content=test_case.content,
        source_fingerprint=test_case.source_fingerprint,
    )

    assert artifact.source_fingerprint == test_case.expected_fingerprint
    assert parse_spy.call_count == test_case.expected_parse_count
    assert hash_spy.call_count == test_case.expected_hash_count
