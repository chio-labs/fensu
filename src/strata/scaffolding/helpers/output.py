"""Transcript rendering through Strata's semantic CLI style facade."""

from __future__ import annotations

import keyword
import re
from io import StringIO
from pathlib import Path
from typing import TextIO

from strata.reporting.classes.cli_style import CliStyle
from strata.scaffolding.constants import (
    ADOPTION_LINK,
    CANDIDATE_PATH_WIDTH,
    CURRENT_PATH_TEXT,
    DRIFT_FAMILY_NAME_WIDTH,
    EDIT_RESPONSE,
    END_OF_INPUT,
    END_OF_INPUT_LABEL,
    MAX_INVALID_ATTEMPTS,
    NO_RESPONSE,
    PARENT_PATH_PART,
    TEST_MARKER_PATH,
    YES_RESPONSE,
)
from strata.scaffolding.exceptions import InitError, InitRefusalError
from strata.scaffolding.models import DriftSummary, InitPlan, PathCandidate
from strata.scaffolding.types import AdoptionMode


def write_header(*, stdout: TextIO, style: CliStyle, text: str, success: bool = False) -> None:
    """Write one canonical arrow section header."""

    rendered: str = style.success(text) if success else style.header_text(text)
    stdout.write(f"{style.header_marker()} {rendered}\n")


def normalize_project_name(*, value: str) -> str:
    """Convert a distribution-like name into a valid Python identifier."""

    normalized: str = re.sub(r"\W+", "_", value.strip(), flags=re.ASCII).strip("_").lower()
    if normalized and normalized[0].isdigit():
        normalized = f"_{normalized}"
    if keyword.iskeyword(normalized):
        normalized = f"{normalized}_"
    if not normalized or not normalized.isidentifier():
        raise InitError(f"Project name cannot be normalized to a Python identifier: {value!r}.")
    return normalized


def write_detected_layout(
    *,
    stdout: TextIO,
    style: CliStyle,
    roots: tuple[PathCandidate, ...],
    tests: tuple[PathCandidate, ...],
    tooling: tuple[PathCandidate, ...],
) -> None:
    """Write detected candidates and provenance without asking absent scopes."""

    write_header(stdout=stdout, style=style, text="Detecting project layout")
    stdout.write("\n")
    if len(roots) > 1:
        stdout.write("    Found package roots:\n")
        column_width: int = max(CANDIDATE_PATH_WIDTH, *(len(candidate.path) for candidate in roots))
        for index, candidate in enumerate(roots, start=1):
            padding: str = " " * (column_width - len(candidate.path) + 1)
            stdout.write(
                f"      {index}) {style.path(candidate.path)}{padding}"
                f"{style.provenance(candidate.provenance.value)}\n"
            )
    else:
        _candidate_row(
            stdout=stdout, style=style, label="roots", candidates=roots, trailing_slash=False
        )
    _candidate_row(stdout=stdout, style=style, label="tests", candidates=tests, trailing_slash=True)
    if tooling:
        _candidate_row(
            stdout=stdout,
            style=style,
            label="tooling",
            candidates=tooling,
            trailing_slash=True,
        )
    else:
        stdout.write(f"    tooling  {style.absent('none detected')}\n")
    stdout.write("\n")


def write_classification(
    *, stdout: TextIO, style: CliStyle, plan: InitPlan, python_file_count: int
) -> None:
    """Write new/existing classification, starting ruleset, and config success."""

    classification: str = "Existing codebase" if python_file_count else "New codebase"
    file_word: str = "file" if python_file_count == 1 else "files"
    stdout.write(
        f"{style.header_marker()} {style.header_text(classification)} "
        f"{style.provenance(f'- {python_file_count:,} Python {file_word}')}\n"
    )
    rules: str = "SF" if plan.adoption is AdoptionMode.FULL else "SFL, SFX, SFA, SFN"
    label: str = "full" if plan.adoption is AdoptionMode.FULL else "gradual"
    stdout.write(f"\n    Starting with the {label} ruleset: {style.value(rules)}\n")
    stdout.write(f"    Wrote {style.success('strata.toml')}\n")


def write_empty_success(*, stdout: TextIO, style: CliStyle, created_paths: tuple[str, ...]) -> None:
    """Write scaffold paths and config success for an empty repository."""

    for path in created_paths:
        display: str = "tests/" if path == TEST_MARKER_PATH else path
        stdout.write(f"    Created {style.path(display)}\n")
    stdout.write(f"    Wrote {style.success('strata.toml')}\n")


def write_drift(*, stdout: TextIO, style: CliStyle, summary: DriftSummary) -> None:
    """Write selected-family totals and a unique-file aggregate only."""

    if summary.fault_count == 0:
        stdout.write("\n")
        write_header(stdout=stdout, style=style, text="Found 0 faults", success=True)
        return
    stdout.write("\n")
    write_header(stdout=stdout, style=style, text="Measuring current drift")
    stdout.write("\n")
    for code, name, count in summary.family_counts:
        padding: str = " " * max(DRIFT_FAMILY_NAME_WIDTH - len(name), 0)
        stdout.write(
            f"    {style.family_fault_code(code)}  {style.provenance(name)}{padding} {count:>7,}\n"
        )
    fault_word: str = "fault" if summary.fault_count == 1 else "faults"
    file_word: str = "file" if summary.file_count == 1 else "files"
    count_text: str = f"{summary.fault_count:,} {fault_word}"
    stdout.write(
        f"\n    Found {style.fault_count(count_text)} across {summary.file_count:,} {file_word}"
        " against the starting ruleset.\n"
    )
    stdout.write(f"    See {style.link(ADOPTION_LINK)} for rolling out gradually.\n")


def write_next(*, stdout: TextIO, style: CliStyle) -> None:
    """Write concise follow-up commands."""

    stdout.write("\n")
    write_header(stdout=stdout, style=style, text="Next")
    stdout.write("\n")
    stdout.write(f"    {style.value('strata check')}            {style.hint('run anytime')}\n")
    stdout.write(
        f"    {style.value('strata rule SFA001')}      "
        f"{style.hint('inspect any code in the output')}\n"
    )


def _candidate_row(
    *,
    stdout: TextIO,
    style: CliStyle,
    label: str,
    candidates: tuple[PathCandidate, ...],
    trailing_slash: bool,
) -> None:
    if not candidates:
        stdout.write(f"    {label:<8} {style.absent('none detected')}\n")
        return
    displays: tuple[str, ...] = tuple(
        f"{candidate.path}/" if trailing_slash else candidate.path for candidate in candidates
    )
    rendered_paths: tuple[str, ...] = tuple(
        style.path(display) if candidate.present else style.absent(display)
        for candidate, display in zip(candidates, displays, strict=True)
    )
    raw_paths: str = ", ".join(displays)
    rendered: str = ", ".join(rendered_paths)
    provenance: str = ", ".join(candidate.provenance.value for candidate in candidates)
    padding: str = " " * max(CANDIDATE_PATH_WIDTH - len(raw_paths), 1)
    stdout.write(f"    {label:<8} {rendered}{padding}{style.provenance(provenance)}\n")


def prompt_accept_layout(*, stdin: TextIO, stdout: TextIO, style: CliStyle) -> bool:
    """Return whether aggregate choices are accepted, or request field editing."""

    value: str = _choice(
        stdin=stdin,
        stdout=stdout,
        prompt=f"    Accept? {style.hint('[Y/n/e]')} ",
        allowed=(YES_RESPONSE, NO_RESPONSE, EDIT_RESPONSE),
        default=YES_RESPONSE,
        prompt_name="layout confirmation",
    )
    if value == NO_RESPONSE:
        raise InitRefusalError("Initialization declined; no files were written.")
    return value == YES_RESPONSE


def prompt_yes_no(
    *, stdin: TextIO, stdout: TextIO, style: CliStyle, prompt: str, default: bool = True
) -> bool:
    """Read one defaulted yes/no decision."""

    hint: str = "[Y/n]" if default else "[y/N]"
    default_value: str = YES_RESPONSE if default else NO_RESPONSE
    value: str = _choice(
        stdin=stdin,
        stdout=stdout,
        prompt=f"{prompt} {style.hint(hint)} ",
        allowed=(YES_RESPONSE, NO_RESPONSE),
        default=default_value,
        prompt_name="yes/no confirmation",
    )
    return value == YES_RESPONSE


def prompt_root_selection(
    *, stdin: TextIO, stdout: TextIO, style: CliStyle, candidates: tuple[PathCandidate, ...]
) -> tuple[str, ...]:
    """Select one or more numbered runtime candidates, defaulting to all."""

    hint: str = '[Enter = all, or e.g. "1,3"]'
    raw: str = END_OF_INPUT
    for attempt in range(MAX_INVALID_ATTEMPTS):
        stdout.write(f"    Include which? {style.hint(hint)} ")
        stdout.flush()
        raw = _read_response(stdin=stdin, stdout=stdout, prompt_name="runtime root selection")
        if not raw:
            return tuple(candidate.path for candidate in candidates)
        selected: tuple[str, ...] | None = _selected_candidates(raw=raw, candidates=candidates)
        if selected is not None:
            return selected
        _invalid(stdout=stdout, attempt=attempt, value=raw)
    raise InitError(f"Invalid root selection after 3 attempts. Final raw value: {raw!r}.")


def prompt_paths(
    *, stdin: TextIO, stdout: TextIO, style: CliStyle, field: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    """Read a comma-separated repository-relative path field."""

    default_text: str = ", ".join(default)
    hint: str = f"[{default_text}]" if default_text else '[e.g. "src/acme"]'
    raw: str = END_OF_INPUT
    for attempt in range(MAX_INVALID_ATTEMPTS):
        stdout.write(f"    {field} {style.hint(hint)}: ")
        stdout.flush()
        raw = _read_response(stdin=stdin, stdout=stdout, prompt_name=field)
        if not raw and default:
            return default
        paths: tuple[str, ...] | None = _parse_paths(raw=raw)
        if paths is not None:
            return paths
        _invalid(stdout=stdout, attempt=attempt, value=raw)
    raise InitError(f"Invalid {field} value after 3 attempts. Final raw value: {raw!r}.")


def prompt_project_name(
    *, stdin: TextIO, stdout: TextIO, style: CliStyle, repository_name: str
) -> str:
    """Read and normalize a project name with the repository basename as default."""

    default_name: str = normalize_project_name(value=repository_name)
    hint: str = (
        f"[{repository_name} -> {default_name}]"
        if repository_name != default_name
        else f"[{default_name}]"
    )
    raw: str = END_OF_INPUT
    for attempt in range(MAX_INVALID_ATTEMPTS):
        stdout.write(f"    Project name {style.hint(hint)}: ")
        stdout.flush()
        raw = _read_response(stdin=stdin, stdout=stdout, prompt_name="project name")
        try:
            name: str = normalize_project_name(value=raw or repository_name)
        except InitError:
            _invalid(stdout=stdout, attempt=attempt, value=raw)
            continue
        stdout.write("\n")
        return name
    raise InitError(f"Invalid project name after 3 attempts. Final raw value: {raw!r}.")


def _choice(
    *,
    stdin: TextIO,
    stdout: TextIO,
    prompt: str,
    allowed: tuple[str, ...],
    default: str,
    prompt_name: str,
) -> str:
    raw: str = END_OF_INPUT
    for attempt in range(MAX_INVALID_ATTEMPTS):
        stdout.write(prompt)
        stdout.flush()
        raw = _read_response(stdin=stdin, stdout=stdout, prompt_name=prompt_name).lower()
        value: str = raw or default
        normalized: str = {"yes": YES_RESPONSE, "no": NO_RESPONSE}.get(value, value)
        if normalized in allowed:
            return normalized
        _invalid(stdout=stdout, attempt=attempt, value=raw)
    raise InitError(
        f"Invalid response after 3 attempts; expected {'/'.join(allowed)}. "
        f"Final raw value: {raw!r}."
    )


def _selected_candidates(
    *, raw: str, candidates: tuple[PathCandidate, ...]
) -> tuple[str, ...] | None:
    try:
        indexes: tuple[int, ...] = tuple(int(part.strip()) for part in raw.split(","))
    except ValueError:
        return None
    if not indexes or len(set(indexes)) != len(indexes):
        return None
    if any(index < 1 or index > len(candidates) for index in indexes):
        return None
    return tuple(candidates[index - 1].path for index in indexes)


def _parse_paths(*, raw: str) -> tuple[str, ...] | None:
    values: tuple[str, ...] = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        return None
    paths: tuple[Path, ...] = tuple(Path(value) for value in values)
    if any(
        path.is_absolute() or PARENT_PATH_PART in path.parts or path.as_posix() == CURRENT_PATH_TEXT
        for path in paths
    ):
        return None
    normalized: tuple[str, ...] = tuple(path.as_posix() for path in paths)
    return normalized if len(set(normalized)) == len(normalized) else None


def _invalid(*, stdout: TextIO, attempt: int, value: str) -> None:
    remaining: int = MAX_INVALID_ATTEMPTS - attempt - 1
    if remaining:
        stdout.write(f"    Invalid response {value!r}; try again.\n")


def _read_response(*, stdin: TextIO, stdout: TextIO, prompt_name: str) -> str:
    """Terminate prompts for injected StringIO streams without duplicating real terminal echo."""

    raw: str = stdin.readline()
    if isinstance(stdout, StringIO):
        stdout.write("\n")
    if raw == END_OF_INPUT:
        raise InitError(
            f"Unexpected EOF while reading {prompt_name}; "
            f"offending raw value: {END_OF_INPUT_LABEL}."
        )
    return raw.strip()
