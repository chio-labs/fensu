"""Parse discovered files into evaluation models."""

from __future__ import annotations

import hashlib
from pathlib import Path

from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.main.build import build_analysis
from strata.analysis.main.parse_source import parse_python_source
from strata.analysis.types import AnalysisBuild, PythonSourceArtifact
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
    try:
        artifact: PythonSourceArtifact = parse_python_source(
            path=scoped_file.path,
            content=snapshot.content,
            source_fingerprint=snapshot.fingerprint,
        )
    except PythonSourceParseError as error:
        message: str = (
            f"Could not parse {scoped_file.path}: syntax is not valid for the Python "
            "interpreter running strata. Run strata under the target project's Python "
            "version or newer."
        )
        raise ParseError(
            path=scoped_file.path, message=message, line=error.line, column=error.column
        ) from error
    build: AnalysisBuild = build_analysis(
        path=artifact.path, source=artifact.source, module=artifact.module
    )
    return ParsedModule(
        scoped_file=scoped_file,
        module=artifact.module,
        source=artifact.source,
        source_fingerprint=artifact.source_fingerprint,
        node_index=build.node_index,
        parent_by_node=build.parent_by_node,
        position=position_facts(scoped_file),
        analysis=build.analysis,
    )
