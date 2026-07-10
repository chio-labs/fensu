"""Test case types for benchmark tooling."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessBenchmarkTestCase:
    """Fake check output and expected benchmark identity."""

    description: str
    runs: int
    output: str
    expected_sha256: str
    expected_summary: str
    expected_output_bytes: int


@dataclass(frozen=True)
class BenchmarkErrorTestCase:
    """Unstable fake check and expected benchmark error."""

    description: str
    runs: int
    expected_error_fragment: str
