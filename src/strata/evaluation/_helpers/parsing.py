"""Parse discovered files into evaluation models."""

from __future__ import annotations

import hashlib
from pathlib import Path

from strata.analysis.classes.file_analysis import PythonFileAnalysis
from strata.analysis.classes.lazy_syntax_artifacts import LazySyntaxArtifacts
from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.main.decode_source import decode_python_source
from strata.analysis.main.extract_native_fact_rows import extract_native_fact_rows
from strata.analysis.main.parse_native_program import parse_native_program
from strata.analysis.main.parse_native_programs import parse_native_programs
from strata.analysis.main.parse_source import parse_python_source
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend, PythonSourceArtifact
from strata.discovery.main.position import position_facts
from strata.discovery.models import ScopedFile
from strata.discovery.types import ScopeName
from strata.evaluation.exceptions import ParseError
from strata.evaluation.models import ParsedModule, SourceSnapshot
from strata.evaluation.types import EvaluationProjectAnalysis

_RUNTIME_FACT_FAMILIES: tuple[str, ...] = (
    "annotations",
    "contracts",
    "control_flow",
    "declarations",
    "functions",
    "hygiene",
    "outer_state_mutations",
    "parameter_mutations",
    "references",
)
_TEST_FACT_FAMILIES: tuple[str, ...] = (
    "annotations",
    "control_flow",
    "references",
    "test_functions",
    "test_module",
)


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
    native_parsed: ParsedModule | None = _parse_native_scoped_file(
        scoped_file=scoped_file, snapshot=snapshot
    )
    if native_parsed is not None:
        return native_parsed
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
    artifacts: LazySyntaxArtifacts = LazySyntaxArtifacts(
        path=artifact.path, source=artifact.source, module=artifact.module
    )
    return _build_parsed_module(
        scoped_file=scoped_file,
        source=artifact.source,
        source_fingerprint=artifact.source_fingerprint,
        artifacts=artifacts,
        program=None,
    )


def prewarm_scoped_files(
    *,
    project: EvaluationProjectAnalysis,
    scoped_files: tuple[ScopedFile, ...],
) -> None:
    """Batch-parse upcoming discovered files natively and seed the project."""

    if select_fact_backend().backend is not FactBackend.NATIVE:
        return
    readable: list[tuple[ScopedFile, SourceSnapshot, str]] = []
    for scoped_file in scoped_files:
        try:
            snapshot: SourceSnapshot = read_source_snapshot(path=scoped_file.path)
            source: str = decode_python_source(path=scoped_file.path, content=snapshot.content)
        except (OSError, PythonSourceParseError):
            continue
        readable.append((scoped_file, snapshot, source))
    programs: tuple[object | None, ...] = parse_native_programs(
        sources=tuple(source for _, _, source in readable)
    )
    _ = extract_native_fact_rows(
        requests=tuple(
            (program, _prewarm_fact_families(scoped_file))
            for (scoped_file, _, _), program in zip(readable, programs, strict=True)
            if program is not None
        )
    )
    for (scoped_file, snapshot, source), program in zip(readable, programs, strict=True):
        if program is None:
            continue
        artifacts: LazySyntaxArtifacts = LazySyntaxArtifacts(path=scoped_file.path, source=source)
        project.prewarm(
            parsed=_build_parsed_module(
                scoped_file=scoped_file,
                source=source,
                source_fingerprint=snapshot.fingerprint,
                artifacts=artifacts,
                program=program,
            )
        )


def _prewarm_fact_families(scoped_file: ScopedFile) -> tuple[str, ...]:
    if scoped_file.scope is ScopeName.TEST:
        return _TEST_FACT_FAMILIES
    return _RUNTIME_FACT_FAMILIES


def _parse_native_scoped_file(
    *, scoped_file: ScopedFile, snapshot: SourceSnapshot
) -> ParsedModule | None:
    try:
        source: str = decode_python_source(path=scoped_file.path, content=snapshot.content)
    except PythonSourceParseError:
        return None
    program: object | None = parse_native_program(source=source)
    if program is None:
        return None
    artifacts: LazySyntaxArtifacts = LazySyntaxArtifacts(path=scoped_file.path, source=source)
    return _build_parsed_module(
        scoped_file=scoped_file,
        source=source,
        source_fingerprint=snapshot.fingerprint,
        artifacts=artifacts,
        program=program,
    )


def _build_parsed_module(
    *,
    scoped_file: ScopedFile,
    source: str,
    source_fingerprint: str,
    artifacts: LazySyntaxArtifacts,
    program: object | None,
) -> ParsedModule:
    analysis: PythonFileAnalysis = PythonFileAnalysis(
        path=scoped_file.path,
        source=source,
        artifacts=artifacts,
        program=program,
    )
    return ParsedModule(
        scoped_file=scoped_file,
        source=source,
        source_fingerprint=source_fingerprint,
        syntax_artifacts=artifacts,
        position=position_facts(scoped_file),
        analysis=analysis,
    )
