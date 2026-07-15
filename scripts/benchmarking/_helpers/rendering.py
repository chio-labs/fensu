"""Render phase, family, and rule profiling results."""

from __future__ import annotations

from scripts.benchmarking.models import OperationReport, ProfileReport

_NANOSECONDS_SUFFIX: str = "_nanoseconds"
_NANOSECONDS_PER_SECOND: int = 1_000_000_000


def render_profile(*, report: ProfileReport, rule_limit: int = 20) -> str:
    """Render one profile with the most expensive rules first."""

    lines: list[str] = [
        f"files={report.file_count} faults={report.fault_count} rules={report.rule_count}",
        f"config={report.config_seconds:.4f}",
        f"discovery={report.discovery_seconds:.4f}",
        f"catalogue={report.catalogue_seconds:.4f}",
        f"evaluation={report.evaluation_seconds:.4f}",
        f"  parse_index={report.parse_seconds:.4f}",
        f"  query_parse_within_rules={report.query_parse_seconds:.4f}",
        f"  rule_execution={report.rule_seconds:.4f}",
        f"  engine_overhead_sort={report.engine_seconds:.4f}",
        f"render={report.render_seconds:.4f} bytes={report.rendered_bytes}",
        "families:",
    ]
    for family, seconds in report.family_seconds:
        lines.append(f"  {family} seconds={seconds:.4f}")
    lines.append("top_rules:")
    for code, seconds, calls in report.rule_timings[:rule_limit]:
        lines.append(f"  {code} seconds={seconds:.4f} calls={calls}")
    return "\n".join(lines)


def render_operations(*, report: OperationReport) -> str:
    """Render deterministic counts and phase seconds for one cache state."""

    lines: list[str] = [f"operation_mode={report.mode}"]
    for operation, count in report.counts:
        if operation.endswith(_NANOSECONDS_SUFFIX):
            seconds: float = count / _NANOSECONDS_PER_SECOND
            lines.append(f"{operation.removesuffix(_NANOSECONDS_SUFFIX)}_seconds={seconds:.6f}")
        else:
            lines.append(f"{operation}={count}")
    return "\n".join(lines)
