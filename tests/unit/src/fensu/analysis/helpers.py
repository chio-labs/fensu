"""Helpers for backend-neutral analysis tests."""

import ast
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

from fensu.analysis.main.build import build_analysis
from fensu.analysis.models import (
    DefinitionIdentity,
    EvaluateRuleCallFact,
    FunctionContractFact,
    SourceLocation,
)
from fensu.analysis.types import Analysis

FAKE_NATIVE_VERSION: str = "9.9.9"
_FACT_FAMILY_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "annotations",
        "assignment_references",
        "class_declarations",
        "comments",
        "comparisons",
        "complex_comprehensions",
        "dataclasses",
        "evaluate_rule_calls",
        "function_conditionals",
        "function_contracts",
        "functions",
        "hygiene",
        "local_call_edges",
        "meaningful_returns",
        "module_declarations",
        "named_calls",
        "outer_state_mutations",
        "parameter_mutations",
        "parameter_mutation_occurrences",
        "project_calls",
        "project_functions",
        "references",
        "test_functions",
        "test_module",
        "top_level_definition_conditionals",
    }
)


def fake_find_spec(*, available: bool) -> Callable[[str], object | None]:
    """Return a find_spec stand-in reporting the requested availability."""

    specs: dict[bool, object | None] = {True: object(), False: None}
    spec: object | None = specs[available]
    return lambda name: spec


def fake_import_module(name: str) -> ModuleType:
    """Return a module stand-in exposing the fake native version."""

    module: SimpleNamespace = SimpleNamespace(backend_version=lambda: FAKE_NATIVE_VERSION)
    return cast(ModuleType, module)


def fact_analysis_owners(*, root: Path) -> tuple[str, ...]:
    """Return concrete classes implementing the complete semantic fact protocol."""

    owners: list[str] = []
    for path in sorted(root.rglob("*.py")):
        module: ast.Module = ast.parse(path.read_text(encoding="utf-8"))
        classes: filter[ast.stmt] = filter(
            lambda declaration: isinstance(declaration, ast.ClassDef), module.body
        )
        for statement in classes:
            declaration: ast.ClassDef = cast(ast.ClassDef, statement)
            functions: filter[ast.stmt] = filter(
                lambda child: isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef),
                declaration.body,
            )
            methods: frozenset[str] = frozenset(
                cast(ast.FunctionDef | ast.AsyncFunctionDef, child).name for child in functions
            )
            protocol: bool = any(
                isinstance(base, ast.Name) and base.id == "Protocol" for base in declaration.bases
            )
            relative: str = path.relative_to(root).as_posix()
            owner: str = f"{relative}:{declaration.name}"
            matching: dict[bool, tuple[str, ...]] = {
                True: (owner,),
                False: (),
            }
            owners.extend(matching[_FACT_FAMILY_METHOD_NAMES <= methods and not protocol])
    return tuple(owners)


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


def definition_line(identity: DefinitionIdentity | None) -> int | None:
    """Return an optional definition identity line."""

    location: SourceLocation | None = getattr(identity, "location", None)
    return getattr(location, "line", None)


def build_test_analysis(*, path: Path, source: str) -> Analysis:
    """Build one analysis facade for static fact tests."""

    return build_analysis(path=path, source=source, module=ast.parse(source))


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
