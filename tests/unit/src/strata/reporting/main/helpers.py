"""Helpers for report rendering tests."""

from __future__ import annotations

from pathlib import Path

from strata.rules.authoring.models import Fault


def make_faults(root: Path) -> tuple[Fault, ...]:
    """Build representative faults for text rendering."""

    path: Path = root / "src" / "pkg" / "a.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("alpha = 1\nbeta = 2\n", encoding="utf-8")
    return (
        Fault(code="XRP001", path=path, line=2, column=4, message="first"),
        Fault(code="XRP002", path=root / "src" / "pkg" / "b.py", message="second"),
    )


def make_missing_source_fault(root: Path) -> tuple[Fault, ...]:
    """Build a fault whose source file is unavailable to the reporter."""

    return (
        Fault(
            code="XRP003",
            path=root / "src" / "pkg" / "missing.py",
            line=1,
            column=0,
            message="missing source",
        ),
    )


def make_missing_column_fault(root: Path) -> tuple[Fault, ...]:
    """Build a line-localized fault without a column position."""

    path: Path = root / "src" / "pkg" / "line_only.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("line_only = True\n", encoding="utf-8")
    return (Fault(code="XRP004", path=path, line=1, message="line only"),)


def make_remediated_fault(root: Path) -> tuple[Fault, ...]:
    """Build a fault with long actionable help text."""

    return (
        Fault(
            code="XRP005",
            path=root / "src/pkg/main/run.py",
            message="main/ entry contains phase implementation",
            remediation=(
                "Move phase implementation into helpers/ and keep main/ focused on ordered "
                "phase calls that return explicit result models."
            ),
        ),
    )
