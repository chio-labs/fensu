"""Benchmark result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckRun:
    """One complete Strata process result."""

    elapsed_seconds: float
    output: bytes
    return_code: int


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Repeated process timings with one stable diagnostic identity."""

    elapsed_seconds: tuple[float, ...]
    output_sha256: str
    output_bytes: int
    fault_summary: str


@dataclass(frozen=True, slots=True)
class ProfileReport:
    """One instrumented check split into phases, families, and rules."""

    file_count: int
    fault_count: int
    rule_count: int
    config_seconds: float
    discovery_seconds: float
    catalogue_seconds: float
    evaluation_seconds: float
    parse_seconds: float
    query_parse_seconds: float
    rule_seconds: float
    engine_seconds: float
    render_seconds: float
    rendered_bytes: int
    family_seconds: tuple[tuple[str, float], ...]
    rule_timings: tuple[tuple[str, float, int], ...]
