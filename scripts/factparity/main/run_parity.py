"""Run fact-backend parity comparison over configured roots."""

from __future__ import annotations

from pathlib import Path

from scripts.factparity._helpers.comparison import compare_file
from scripts.factparity.constants import MAX_REPORTED_DIFFS
from scripts.factparity.models import FamilyDiff, ParityReport
from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.main.parse_source import parse_python_source
from strata.analysis.types import PythonSourceArtifact


def run_parity(*, roots: tuple[Path, ...]) -> int:
    """Compare every fact family across backends and report divergence."""

    report: ParityReport = _collect_report(roots=roots)
    for diff in report.diffs[:MAX_REPORTED_DIFFS]:
        print(f"DIFF {diff.path} :: {diff.family}")
        print(f"  python: {diff.expected}")
        print(f"  native: {diff.actual}")
    print(
        f"factparity: {report.checked_file_count} files compared, "
        f"{report.skipped_file_count} skipped, {len(report.diffs)} family diffs"
    )
    return 1 if report.diffs else 0


def _collect_report(*, roots: tuple[Path, ...]) -> ParityReport:
    checked: int = 0
    skipped: int = 0
    diffs: list[FamilyDiff] = []
    for root in roots:
        for file_path in sorted(root.rglob("*.py")):
            try:
                artifact: PythonSourceArtifact = parse_python_source(
                    path=file_path,
                    content=file_path.read_bytes(),
                )
            except PythonSourceParseError:
                skipped += 1
                continue
            checked += 1
            diffs.extend(
                compare_file(
                    path=file_path,
                    source=artifact.source,
                    module=artifact.module,
                )
            )
    return ParityReport(
        checked_file_count=checked,
        skipped_file_count=skipped,
        diffs=tuple(diffs),
    )
