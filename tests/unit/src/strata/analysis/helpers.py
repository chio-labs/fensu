"""Helpers for backend-neutral analysis tests."""

import ast
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

from strata.analysis.classes.fact_analysis import PythonFactAnalysis
from strata.analysis.classes.native_fact_analysis import NativeFactAnalysis
from strata.analysis.main.build import build_analysis
from strata.analysis.models import EvaluateRuleCallFact, FunctionContractFact, SourceLocation
from strata.analysis.types import Analysis, FactAnalysis

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

FAKE_NATIVE_VERSION: str = "9.9.9"


def fake_find_spec(*, available: bool) -> Callable[[str], object | None]:
    """Return a find_spec stand-in reporting the requested availability."""

    specs: dict[bool, object | None] = {True: object(), False: None}
    spec: object | None = specs[available]
    return lambda name: spec


def fake_import_module(name: str) -> ModuleType:
    """Return a module stand-in exposing the fake native version."""

    module: SimpleNamespace = SimpleNamespace(backend_version=lambda: FAKE_NATIVE_VERSION)
    return cast(ModuleType, module)


def sentinel_fact_analysis(*, method_names: tuple[str, ...]) -> FactAnalysis:
    """Return a fact stand-in whose every family reports its own name."""

    methods: dict[str, Callable[..., str]] = {name: _named_sentinel(name) for name in method_names}
    return cast(FactAnalysis, SimpleNamespace(**methods))


def _named_sentinel(name: str) -> Callable[..., str]:
    return lambda **kwargs: name


def cpython_parse_validity(source: str) -> bool:
    """Return whether ast.parse accepts the source, mirroring the strict path."""

    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


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


def fact_family_divergences(*, path: Path, source: str) -> tuple[str, ...]:
    """Return fact families whose Python and native backends disagree."""

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
        matching: dict[bool, tuple[str, ...]] = {True: (), False: (family,)}
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
