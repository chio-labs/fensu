"""Parse discovered files into evaluation models."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from strata.analysis.main.build import build_analysis
from strata.analysis.types import AnalysisBuild
from strata.discovery.main.position import position_facts
from strata.discovery.models import ScopedFile
from strata.evaluation.exceptions import ParseError
from strata.evaluation.models import ParsedModule, SourceSnapshot


def read_source_snapshot(*, path: Path) -> SourceSnapshot:
    """Read source bytes once and return their stable identity."""

    content: bytes = path.read_bytes()
    return SourceSnapshot(content=content, fingerprint=hashlib.sha256(content).hexdigest())


def parse_scoped_file(
    *,
    scoped_file: ScopedFile,
    source_snapshot: SourceSnapshot | None = None,
) -> ParsedModule:
    """Read and parse one discovered Python file."""

    snapshot: SourceSnapshot = source_snapshot or read_source_snapshot(path=scoped_file.path)
    source: str = decode_source_snapshot(snapshot)
    try:
        module: ast.Module = ast.parse(source, filename=str(scoped_file.path))
    except SyntaxError as error:
        message: str = (
            f"Could not parse {scoped_file.path}: syntax is not valid for the Python "
            "interpreter running strata. Run strata under the target project's Python "
            "version or newer."
        )
        raise ParseError(
            path=scoped_file.path, message=message, line=error.lineno, column=error.offset
        ) from error
    analysis_build: AnalysisBuild = build_analysis(
        path=scoped_file.path, source=source, module=module
    )
    return ParsedModule(
        scoped_file=scoped_file,
        module=module,
        source=source,
        source_fingerprint=snapshot.fingerprint,
        node_index=analysis_build.node_index,
        parent_by_node=analysis_build.parent_by_node,
        position=position_facts(scoped_file),
        analysis=analysis_build.analysis,
    )


def decode_source_snapshot(snapshot: SourceSnapshot) -> str:
    """Decode source bytes with the universal newline behavior used by text reads."""

    source: str = snapshot.content.decode("utf-8")
    return source.replace("\r\n", "\n").replace("\r", "\n")
