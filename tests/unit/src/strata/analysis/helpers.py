"""Helpers for backend-neutral analysis tests."""

import ast
from pathlib import Path

from strata.analysis.main.build import build_analysis
from strata.analysis.models import EvaluateRuleCallFact, FunctionContractFact, SourceLocation
from strata.analysis.types import Analysis


def meaningful_return_lines(facts: tuple[FunctionContractFact, ...]) -> tuple[int | None, ...]:
    """Return optional meaningful-return lines from contract facts."""

    lines: list[int | None] = []
    for fact in facts:
        location: SourceLocation | None = fact.meaningful_return_location
        lines.append(getattr(location, "line", None))
    return tuple(lines)


def build_test_analysis(*, path: Path, source: str) -> Analysis:
    """Build one analysis facade for static fact tests."""

    return build_analysis(path=path, source=source, module=ast.parse(source)).analysis


def build_module_analyses(
    *, root: Path, module_names: tuple[str, ...], module_sources: tuple[str, ...]
) -> dict[str, Analysis]:
    """Build analyses keyed by importable module name."""

    analyses: dict[str, Analysis] = {}
    for module_name, source in zip(module_names, module_sources, strict=True):
        path: Path = root.joinpath(*module_name.split(".")).with_suffix(".py")
        analyses[module_name] = build_test_analysis(path=path, source=source)
    return analyses


def rule_case_location_lines(
    calls: tuple[EvaluateRuleCallFact, ...],
) -> tuple[tuple[int, ...], ...]:
    """Return nested literal case lines without a nested comprehension."""

    call_lines: list[tuple[int, ...]] = []
    for call in calls:
        lines: list[int] = []
        for location in call.case_locations:
            lines.append(location.line)
        call_lines.append(tuple(lines))
    return tuple(call_lines)
