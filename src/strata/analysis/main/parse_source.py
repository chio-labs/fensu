"""Decode and parse exact Python source bytes."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.main.decode_source import decode_python_source
from strata.analysis.types import PythonSourceArtifact
from strata.instrumentation.constants import OPERATION_COUNTERS, PARSE_OPERATION


def parse_python_source(
    *, path: Path, content: bytes, source_fingerprint: str | None = None
) -> PythonSourceArtifact:
    """Decode and parse one exact Python source snapshot."""

    OPERATION_COUNTERS.record(operation=PARSE_OPERATION)
    source: str = decode_python_source(path=path, content=content)
    try:
        module: ast.Module = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        raise PythonSourceParseError(
            path=path,
            message=error.msg,
            line=error.lineno,
            column=error.offset,
            rendered=str(error),
        ) from error
    return PythonSourceArtifact(
        path=path,
        source=source,
        source_fingerprint=(
            source_fingerprint
            if source_fingerprint is not None
            else hashlib.sha256(content).hexdigest()
        ),
        module=module,
    )
