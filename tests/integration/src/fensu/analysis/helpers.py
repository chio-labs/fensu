"""Local helpers for parser validity agreement tests."""

import ast
import sys
from contextlib import suppress
from importlib import import_module
from io import BytesIO
from pathlib import Path
from tokenize import detect_encoding
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME


def parse_validity_divergences(*, root: Path) -> tuple[str, ...]:
    """Return files whose strict-parse validity differs between backends."""

    divergent: list[str] = []
    for path in sorted(root.rglob("*.py")):
        source: str = _normalized_source(path.read_bytes())
        agreement: bool = _cpython_validity(source) == _native_validity(source)
        matching: dict[bool, tuple[str, ...]] = {True: (), False: (str(path),)}
        divergent.extend(matching[agreement])
    return tuple(divergent)


def _normalized_source(content: bytes) -> str:
    encoding: str = detect_encoding(BytesIO(content).readline)[0]
    return content.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")


def _cpython_validity(source: str) -> bool:
    outcomes: list[bool] = [False]
    with suppress(SyntaxError):
        ast.parse(source)
        outcomes.append(True)
    return outcomes[-1]


def _native_validity(source: str) -> bool:
    fensu_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    failure: object = fensu_facts.check_syntax(source, sys.version_info[0], sys.version_info[1])
    return failure is None
