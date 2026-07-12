"""Text report rendering helpers."""

from __future__ import annotations

import textwrap
from pathlib import Path

from strata.evaluation.models import ThresholdOverrideUse
from strata.reporting.constants import (
    ANSI_BOLD_GREEN,
    ANSI_BOLD_RED,
    ANSI_DIM,
    ANSI_RESET,
    REPORT_LINE_WIDTH,
)
from strata.rules.authoring.models import Fault


def render_text(
    *,
    faults: tuple[Fault, ...],
    root: Path,
    use_color: bool,
    applied_exception_count: int,
    threshold_override_uses: tuple[ThresholdOverrideUse, ...],
) -> str:
    """Render faults as stable text lines with a summary."""

    lines: list[str] = []
    for fault in faults:
        if lines:
            lines.append("")
        lines.extend(_format_fault(fault=fault, root=root, use_color=use_color))
    count: int = len(faults)
    noun: str = "fault" if count == 1 else "faults"
    if lines:
        lines.append("")
    lines.append(_format_summary(text=f"Found {count} {noun}", count=count, use_color=use_color))
    if applied_exception_count:
        exception_noun: str = "exception" if applied_exception_count == 1 else "exceptions"
        lines.append(f"Applied {applied_exception_count} rule {exception_noun}")
    if threshold_override_uses:
        override_noun: str = "override" if len(threshold_override_uses) == 1 else "overrides"
        lines.append(f"Applied {len(threshold_override_uses)} threshold {override_noun}")
    for use in threshold_override_uses:
        lines.append(
            f"Threshold override: {use.threshold.value}={use.effective_value} "
            f"path={use.repository_path} pattern={use.matched_pattern} "
            f"order={use.override_order} reason={use.reason}"
        )
    return "\n".join(lines)


def _format_fault(*, fault: Fault, root: Path, use_color: bool) -> tuple[str, ...]:
    header: tuple[str, str] = _format_header(fault=fault, root=root, use_color=use_color)
    excerpt: tuple[str, ...] = _format_excerpt(fault=fault, use_color=use_color)
    help_lines: tuple[str, ...] = _format_help(fault=fault, use_color=use_color)
    return (*header, *excerpt, *help_lines)


def _format_header(*, fault: Fault, root: Path, use_color: bool) -> tuple[str, str]:
    if not use_color:
        return _format_plain_fault(fault=fault, root=root)
    location: str = _format_location(fault=fault, root=root)
    return (
        f"{ANSI_BOLD_RED}{fault.code}{ANSI_RESET}  {fault.message}",
        f"{ANSI_DIM} --> {location}{ANSI_RESET}",
    )


def _format_plain_fault(*, fault: Fault, root: Path) -> tuple[str, str]:
    location: str = _format_location(fault=fault, root=root)
    return (f"{fault.code}  {fault.message}", f" --> {location}")


def _format_excerpt(*, fault: Fault, use_color: bool) -> tuple[str, ...]:
    source_line: str | None = _read_source_line(path=fault.path, line=fault.line)
    if source_line is None:
        return ()
    gutter: str = _gutter(line=fault.line)
    caret_column: int = 0 if fault.column is None else max(fault.column, 0)
    caret_padding: str = " " * caret_column
    caret: str = f"{caret_padding}^"
    if use_color:
        return (
            f"{ANSI_DIM}  |{ANSI_RESET}",
            f"{ANSI_DIM}{gutter} |{ANSI_RESET} {source_line}",
            f"{ANSI_DIM}  |{ANSI_RESET} {caret_padding}{ANSI_BOLD_RED}^{ANSI_RESET}",
            f"{ANSI_DIM}  |{ANSI_RESET}",
        )
    return ("  |", f"{gutter} | {source_line}", f"  | {caret}", "  |")


def _format_location(*, fault: Fault, root: Path) -> str:
    try:
        relative_path: Path = fault.path.relative_to(root)
    except ValueError:
        relative_path = fault.path
    line_text: str = str(fault.line) if fault.line is not None else "-"
    column_text: str = str(fault.column) if fault.column is not None else "-"
    return f"{relative_path}:{line_text}:{column_text}"


def _format_help(*, fault: Fault, use_color: bool) -> tuple[str, ...]:
    if fault.remediation is None:
        return ()
    prefix: str = "  = help: "
    continuation: str = "          "
    wrapped: list[str] = textwrap.wrap(
        fault.remediation,
        width=REPORT_LINE_WIDTH,
        initial_indent=prefix,
        subsequent_indent=continuation,
    )
    if not use_color:
        return tuple(wrapped)
    label: str = f"{ANSI_DIM}= help:{ANSI_RESET}"
    first_line: str = wrapped[0].removeprefix(prefix)
    return (f"  {label} {first_line}", *wrapped[1:])


def _read_source_line(*, path: Path, line: int | None) -> str | None:
    if line is None or line < 1:
        return None
    try:
        lines: list[str] = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if line > len(lines):
        return None
    return lines[line - 1]


def _gutter(*, line: int | None) -> str:
    return str(line) if line is not None else "-"


def _format_summary(*, text: str, count: int, use_color: bool) -> str:
    if not use_color:
        return text
    color: str = ANSI_BOLD_RED if count else ANSI_BOLD_GREEN
    return f"{color}{text}{ANSI_RESET}"
