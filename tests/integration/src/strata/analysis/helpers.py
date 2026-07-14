"""Local helpers for parser validity agreement tests."""

import ast
import sys
from collections import defaultdict, deque
from collections.abc import Mapping
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from tokenize import detect_encoding

import strata_facts

from strata.analysis.classes.fact_analysis import PythonFactAnalysis
from strata.analysis.classes.native_fact_analysis import NativeFactAnalysis

FACT_FAMILY_NAMES: tuple[str, ...] = (
    "annotations",
    "comments",
    "complex_comprehensions",
    "dataclasses",
    "evaluate_rule_calls",
    "function_conditionals",
    "function_contracts",
    "functions",
    "hygiene",
    "meaningful_returns",
    "module_declarations",
    "outer_state_mutations",
    "parameter_mutations",
    "project_calls",
    "project_functions",
    "references",
    "test_functions",
    "test_module",
    "top_level_definition_conditionals",
)


def parse_validity_divergences(*, root: Path) -> tuple[str, ...]:
    """Return files whose strict-parse validity differs between backends."""

    divergent: list[str] = []
    for path in sorted(root.rglob("*.py")):
        source: str = _normalized_source(path.read_bytes())
        agreement: bool = _cpython_validity(source) == _native_validity(source)
        matching: dict[bool, tuple[str, ...]] = {True: (), False: (str(path),)}
        divergent.extend(matching[agreement])
    return tuple(divergent)


def _normalized_source(content: bytes) -> str:
    encoding: str = detect_encoding(BytesIO(content).readline)[0]
    return content.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")


def _cpython_validity(source: str) -> bool:
    outcomes: list[bool] = [False]
    with suppress(SyntaxError):
        ast.parse(source)
        outcomes.append(True)
    return outcomes[-1]


def _native_validity(source: str) -> bool:
    failure: object = strata_facts.check_syntax(source, sys.version_info[0], sys.version_info[1])
    return failure is None


def fact_family_divergences(*, root: Path) -> tuple[str, ...]:
    """Return path-qualified fact families whose backends disagree."""

    divergent: list[str] = []
    for path in sorted(root.rglob("*.py")):
        source: str = _normalized_source(path.read_bytes())
        divergent.extend(_file_divergences(path=path, source=source))
    return tuple(divergent)


def _file_divergences(*, path: Path, source: str) -> tuple[str, ...]:
    module: ast.Module = ast.parse(source)
    python_facts: PythonFactAnalysis = _python_fact_backend(path=path, source=source, module=module)
    delegate: PythonFactAnalysis = _python_fact_backend(path=path, source=source, module=module)
    native_facts: NativeFactAnalysis = NativeFactAnalysis(
        python_facts=delegate, path=path, source=source
    )
    divergent: list[str] = []
    for family in FACT_FAMILY_NAMES:
        expected: object = getattr(python_facts, family)()
        actual: object = getattr(native_facts, family)()
        matching: dict[bool, tuple[str, ...]] = {True: (), False: (f"{path}::{family}",)}
        divergent.extend(matching[expected == actual])
    return tuple(divergent)


def _python_fact_backend(*, path: Path, source: str, module: ast.Module) -> PythonFactAnalysis:
    node_index: defaultdict[type[ast.AST], list[ast.AST]] = defaultdict(list)
    parent_by_node: dict[ast.AST, ast.AST] = {}
    nodes: list[ast.AST] = []
    pending: deque[ast.AST] = deque((module,))
    while pending:
        node: ast.AST = pending.popleft()
        nodes.append(node)
        node_index[type(node)].append(node)
        for child in ast.iter_child_nodes(node):
            parent_by_node[child] = node
            pending.append(child)
    frozen_index: Mapping[type[ast.AST], tuple[ast.AST, ...]] = {
        node_type: tuple(indexed) for node_type, indexed in node_index.items()
    }
    return PythonFactAnalysis(
        path=path,
        source=source,
        module=module,
        nodes=tuple(nodes),
        node_index=frozen_index,
        parent_by_node=parent_by_node,
    )
