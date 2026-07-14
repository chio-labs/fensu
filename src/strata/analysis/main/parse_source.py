"""Decode and parse exact Python source bytes."""

from __future__ import annotations

import ast
import hashlib
from io import BytesIO
from pathlib import Path
from tokenize import detect_encoding

from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.types import PythonSourceArtifact
from strata.instrumentation.constants import OPERATION_COUNTERS, PARSE_OPERATION


def parse_python_source(
    *, path: Path, content: bytes, source_fingerprint: str | None = None
) -> PythonSourceArtifact:
    """Decode and parse one exact Python source snapshot."""

    OPERATION_COUNTERS.record(operation=PARSE_OPERATION)
    try:
        encoding: str = detect_encoding(BytesIO(content).readline)[0]
        source: str = content.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
    except (SyntaxError, UnicodeError, LookupError) as error:
        raise PythonSourceParseError(
            path=path,
            message=getattr(error, "msg", str(error)),
            line=getattr(error, "lineno", None),
            column=getattr(error, "offset", None),
            rendered=str(error),
        ) from error
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
