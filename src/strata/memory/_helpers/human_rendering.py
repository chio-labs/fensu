"""Deterministic human-readable Strata Memory rendering."""

from __future__ import annotations

import json

from strata.memory.constants import ANSI_BOLD_CYAN, ANSI_RESET, NULL_TEXT
from strata.memory.models import MemoryQueryResult, MemorySchemaColumn, MemorySchemaRelation
from strata.memory.types import MemoryQueryValue


def heading(*, value: str, use_color: bool) -> str:
    """Render one optional ANSI heading."""

    if use_color:
        return f"{ANSI_BOLD_CYAN}{value}{ANSI_RESET}"
    return value


def query_value(value: MemoryQueryValue) -> str:
    """Render one query value for human and CSV output."""

    if value is None:
        return NULL_TEXT
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return str(value)


def relation_lines(relations: tuple[MemorySchemaRelation, ...]) -> list[str]:
    """Render aligned relation names and meanings."""

    if not relations:
        return ["  (none)"]
    width: int = max(len(relation.name) for relation in relations)
    return [f"  {relation.name:<{width}}  {relation.comment}" for relation in relations]


def column_lines(columns: tuple[MemorySchemaColumn, ...]) -> list[str]:
    """Render a focused relation's column metadata."""

    rows: list[tuple[str, str, str, str]] = [
        (column.name, column.data_type, "yes" if column.nullable else "no", column.comment)
        for column in columns
    ]
    headings: tuple[str, str, str, str] = ("Column", "Type", "Nullable", "Meaning")
    widths: list[int] = [len(value) for value in headings]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    rendered: list[str] = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(headings)).rstrip(),
        "-+-".join("-" * width for width in widths),
    ]
    for row in rows:
        rendered_row: str = " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(row)
        ).rstrip()
        rendered.append(rendered_row)
    return rendered


def query_table(*, result: MemoryQueryResult, use_color: bool) -> str:
    """Render deterministic simple text table output."""

    rendered_rows: list[list[str]] = []
    for row in result.rows:
        rendered_row: list[str] = []
        for value in row:
            rendered_row.append(query_value(value))
        rendered_rows.append(rendered_row)
    widths: list[int] = [len(column) for column in result.columns]
    for row in rendered_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    lines: list[str] = [
        heading(
            value=" | ".join(
                column.ljust(widths[index]) for index, column in enumerate(result.columns)
            ),
            use_color=use_color,
        ),
        "-+-".join("-" * width for width in widths),
    ]
    for row in rendered_rows:
        rendered_line: str = " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(row)
        ).rstrip()
        lines.append(rendered_line)
    lines.append(query_count(result))
    return "\n".join(lines) + "\n"


def query_long(*, result: MemoryQueryResult, use_color: bool) -> str:
    """Render expanded records with duplicate columns preserved."""

    lines: list[str] = []
    label_width: int = max((len(column) for column in result.columns), default=0)
    for record_number, row in enumerate(result.rows, start=1):
        lines.append(heading(value=f"-[ RECORD {record_number} ]-", use_color=use_color))
        for column, value in zip(result.columns, row, strict=True):
            lines.append(f"{column:<{label_width}} | {query_value(value)}")
    lines.append(query_count(result))
    return "\n".join(lines) + "\n"


def query_count(result: MemoryQueryResult) -> str:
    """Render row count and truncation state for human formats."""

    suffix: str = ", truncated" if result.truncated else ""
    count: int = len(result.rows)
    noun: str = "row" if count == 1 else "rows"
    return f"({count} {noun}{suffix})"
