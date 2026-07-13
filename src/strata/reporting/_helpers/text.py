"""Text report rendering helpers."""

from __future__ import annotations

import json
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
    warnings: tuple[Fault, ...],
    root: Path,
    use_color: bool,
    show_warnings: bool,
    applied_exception_count: int,
    threshold_override_uses: tuple[ThresholdOverrideUse, ...],
) -> str:
    """Render faults as stable text lines with a summary."""

    lines: list[str] = []
    for fault in faults:
        if lines:
            lines.append("")
        lines.extend(_format_fault(fault=fault, root=root, use_color=use_color, is_warning=False))
    for warning in warnings:
        if lines:
            lines.append("")
        lines.extend(_format_fault(fault=warning, root=root, use_color=use_color, is_warning=True))
    count: int = len(faults)
    noun: str = "fault" if count == 1 else "faults"
    if lines:
        lines.append("")
    summary: str = f"Found {count} {noun}"
    if show_warnings:
        warning_count: int = len(warnings)
        warning_noun: str = "warning" if warning_count == 1 else "warnings"
        summary = f"{summary} and {warning_count} {warning_noun}"
    lines.append(_format_summary(text=summary, count=count, use_color=use_color))
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
            f"order={use.override_order} reason={json.dumps(use.reason)}"
        )
    return "\n".join(lines)


def _format_fault(
    *, fault: Fault, root: Path, use_color: bool, is_warning: bool
) -> tuple[str, ...]:
    header: tuple[str, str] = _format_header(fault=fault, root=root, use_color=use_color)
    excerpt: tuple[str, ...] = _format_excerpt(fault=fault, use_color=use_color)
    help_lines: tuple[str, ...] = _format_help(
        fault=fault,
        use_color=use_color,
        label="warning" if is_warning else "help",
    )
    if is_warning and not help_lines:
        help_lines = (_format_label(label="warning", use_color=use_color),)
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


def _format_help(*, fault: Fault, use_color: bool, label: str) -> tuple[str, ...]:
    if fault.remediation is None:
        return ()
    prefix: str = f"  = {label}: "
    continuation: str = "          "
    wrapped: list[str] = textwrap.wrap(
        fault.remediation,
        width=REPORT_LINE_WIDTH,
        initial_indent=prefix,
        subsequent_indent=continuation,
    )
    if not use_color:
        return tuple(wrapped)
    styled_label: str = f"{ANSI_DIM}= {label}:{ANSI_RESET}"
    first_line: str = wrapped[0].removeprefix(prefix)
    return (f"  {styled_label} {first_line}", *wrapped[1:])


def _format_label(*, label: str, use_color: bool) -> str:
    text: str = f"  = {label}"
    return f"  {ANSI_DIM}= {label}{ANSI_RESET}" if use_color else text


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
