"""JSON and CSV rendering for Strata Memory queries."""

from __future__ import annotations

import csv
import io
import json
import math
from typing import Any

from strata.memory._helpers.human_rendering import query_value
from strata.memory.models import MemoryQueryResult
from strata.memory.types import MemoryQueryValue


def query_json(result: MemoryQueryResult) -> str:
    """Render a metadata-preserving JSON query envelope."""

    safe_rows: list[list[MemoryQueryValue]] = []
    for row in result.rows:
        safe_row: list[MemoryQueryValue] = []
        for value in row:
            safe_row.append(json_safe(value))
        safe_rows.append(safe_row)
    envelope: dict[str, object] = {
        "columns": list(result.columns),
        "types": list(result.types),
        "rows": safe_rows,
        "truncated": result.truncated,
    }
    return json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def query_csv(result: MemoryQueryResult) -> str:
    """Render valid RFC-style CSV with explicit NULL values."""

    stream: io.StringIO = io.StringIO(newline="")
    writer: Any = csv.writer(stream, lineterminator="\r\n")
    _ = writer.writerow(result.columns)
    for row in result.rows:
        _ = writer.writerow(tuple(query_value(value) for value in row))
    return stream.getvalue()


def json_safe(value: MemoryQueryValue) -> MemoryQueryValue:
    """Recursively normalize values for strict JSON serialization."""

    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    return value
