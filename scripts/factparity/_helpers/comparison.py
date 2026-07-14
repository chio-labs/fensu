"""Compare fact families between the Python and native backends."""

from __future__ import annotations

import ast
from pathlib import Path

from scripts.factparity._helpers.indexing import index_module_nodes
from scripts.factparity.constants import (
    FACT_FAMILY_NAMES,
    MAX_DIFF_REPR_LENGTH,
    MEANINGFUL_RETURN_PATTERNS,
)
from scripts.factparity.models import FamilyDiff
from strata.analysis.classes.fact_analysis import PythonFactAnalysis
from strata.analysis.classes.native_fact_analysis import NativeFactAnalysis


def compare_file(*, path: Path, source: str, module: ast.Module) -> tuple[FamilyDiff, ...]:
    """Return every family whose Python and native facts disagree for one file."""

    python_facts: PythonFactAnalysis = _build_python_facts(path=path, source=source, module=module)
    delegate_facts: PythonFactAnalysis = _build_python_facts(
        path=path, source=source, module=module
    )
    native_facts: NativeFactAnalysis = NativeFactAnalysis(
        python_facts=delegate_facts,
        path=path,
        source=source,
    )
    diffs: list[FamilyDiff] = []
    for family in FACT_FAMILY_NAMES:
        expected: object = getattr(python_facts, family)()
        actual: object = getattr(native_facts, family)()
        if expected != actual:
            diffs.append(_family_diff(path=path, family=family, expected=expected, actual=actual))
    patterned_expected: object = python_facts.meaningful_returns(
        name_patterns=MEANINGFUL_RETURN_PATTERNS
    )
    patterned_actual: object = native_facts.meaningful_returns(
        name_patterns=MEANINGFUL_RETURN_PATTERNS
    )
    if patterned_expected != patterned_actual:
        diffs.append(
            _family_diff(
                path=path,
                family="meaningful_returns(patterned)",
                expected=patterned_expected,
                actual=patterned_actual,
            )
        )
    return tuple(diffs)


def _build_python_facts(*, path: Path, source: str, module: ast.Module) -> PythonFactAnalysis:
    nodes, node_index, parent_by_node = index_module_nodes(module)
    return PythonFactAnalysis(
        path=path,
        source=source,
        module=module,
        nodes=nodes,
        node_index=node_index,
        parent_by_node=parent_by_node,
    )


def _family_diff(*, path: Path, family: str, expected: object, actual: object) -> FamilyDiff:
    return FamilyDiff(
        path=path,
        family=family,
        expected=_first_difference(value=expected, other=actual),
        actual=_first_difference(value=actual, other=expected),
    )


def _first_difference(*, value: object, other: object) -> str:
    if isinstance(value, tuple) and isinstance(other, tuple):
        length: int = min(len(value), len(other))
        for position in range(length):
            if value[position] != other[position]:
                return f"[{position}] {value[position]!r}"[:MAX_DIFF_REPR_LENGTH]
        if len(value) != len(other):
            return f"length {len(value)}: tail {value[length:]!r}"[:MAX_DIFF_REPR_LENGTH]
    return repr(value)[:MAX_DIFF_REPR_LENGTH]
