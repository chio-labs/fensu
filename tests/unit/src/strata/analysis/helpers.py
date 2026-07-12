"""Helpers for backend-neutral analysis tests."""

from strata.analysis.models import FunctionContractFact, SourceLocation


def meaningful_return_lines(facts: tuple[FunctionContractFact, ...]) -> tuple[int | None, ...]:
    """Return optional meaningful-return lines from contract facts."""

    lines: list[int | None] = []
    for fact in facts:
        location: SourceLocation | None = fact.meaningful_return_location
        lines.append(location.line if location is not None else None)
    return tuple(lines)
