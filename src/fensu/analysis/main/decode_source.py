"""Decode exact Python source bytes into normalized text."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tokenize import detect_encoding

from fensu.analysis.exceptions import PythonSourceParseError


def decode_python_source(*, path: Path, content: bytes) -> str:
    """Decode one exact source snapshot with PEP 263 encoding detection."""

    try:
        encoding: str = detect_encoding(BytesIO(content).readline)[0]
        return content.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
    except (SyntaxError, UnicodeError, LookupError) as error:
        raise PythonSourceParseError(
            path=path,
            message=getattr(error, "msg", str(error)),
            line=getattr(error, "lineno", None),
            column=getattr(error, "offset", None),
            rendered=str(error),
        ) from error
