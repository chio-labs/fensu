"""Import and attribute-reference fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.locations import source_location
from strata.analysis.core.models import (
    AttributeReferenceFact,
    ImportAliasFact,
    ImportFact,
    PytestModuleFacts,
    ReferenceFacts,
    SourceLocation,
)

_test_case_list_name: str = "TEST_CASES"
_test_case_list_suffix: str = "_TEST_CASES"
_dataclass_decorator_name: str = "dataclass"


def reference_facts(
    *,
    path: Path,
    module: ast.Module,
    nodes: tuple[ast.AST, ...],
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> ReferenceFacts:
    """Return grouped imports and breadth-first reference events."""

    reference_nodes: tuple[ast.AST, ...] = (
        *node_index.get(ast.ImportFrom, ()),
        *node_index.get(ast.Import, ()),
        *node_index.get(ast.Attribute, ()),
    )
    if not reference_nodes:
        return ReferenceFacts(imports=(), events=())
    import_by_node: dict[ast.AST, ImportFact] = {}
    imports: list[ImportFact] = []
    top_level_nodes: frozenset[ast.AST] = frozenset(module.body)
    for node in (*node_index.get(ast.ImportFrom, ()), *node_index.get(ast.Import, ())):
        if not isinstance(node, ast.ImportFrom | ast.Import):
            continue
        fact: ImportFact = _import_fact(
            path=path,
            node=node,
            top_level=node in top_level_nodes,
        )
        import_by_node[node] = fact
        imports.append(fact)
    events: list[ImportFact | AttributeReferenceFact] = []
    for node in nodes:
        import_fact: ImportFact | None = import_by_node.get(node)
        if import_fact is not None:
            events.append(import_fact)
        elif isinstance(node, ast.Attribute) and _is_private_class_name(node.attr):
            events.append(
                AttributeReferenceFact(
                    location=source_location(path=path, node=node),
                    base_name=_attribute_base_name(node.value),
                    attribute_name=node.attr,
                )
            )
    return ReferenceFacts(imports=tuple(imports), events=tuple(events))


def _import_fact(
    *,
    path: Path,
    node: ast.Import | ast.ImportFrom,
    top_level: bool,
) -> ImportFact:
    if isinstance(node, ast.ImportFrom):
        module_parts: tuple[str, ...] = tuple(node.module.split(".")) if node.module else ()
        aliases: tuple[ImportAliasFact, ...] = tuple(
            ImportAliasFact(
                imported_name=alias.name,
                imported_parts=tuple(alias.name.split(".")),
                bound_name=alias.asname or alias.name,
            )
            for alias in node.names
        )
        relative_level: int = node.level
        from_import: bool = True
    else:
        module_parts = ()
        aliases = tuple(
            ImportAliasFact(
                imported_name=alias.name,
                imported_parts=tuple(alias.name.split(".")),
                bound_name=alias.asname or alias.name.split(".")[-1],
            )
            for alias in node.names
        )
        relative_level = 0
        from_import = False
    return ImportFact(
        location=source_location(path=path, node=node),
        module_parts=module_parts,
        aliases=aliases,
        relative_level=relative_level,
        from_import=from_import,
        top_level=top_level,
    )


def _attribute_base_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _attribute_base_name(node.value)
    return None


def _is_private_class_name(name: str) -> bool:
    return len(name) > 1 and name.startswith("_") and name[1].isupper()


def test_module_facts(*, path: Path, module: ast.Module) -> PytestModuleFacts:
    """Return reusable test module-shape metadata."""

    scenario_invalid: list[SourceLocation] = []
    top_level_helpers: list[SourceLocation] = []
    test_case_lists: list[SourceLocation] = []
    private_after_test: list[SourceLocation] = []
    found_test_function: bool = False
    for node in module.body:
        location: SourceLocation = source_location(path=path, node=node)
        if not _is_docstring_statement(node) and not isinstance(node, ast.Import | ast.ImportFrom):
            if not isinstance(node, ast.ClassDef) or not _has_dataclass_decorator(node):
                scenario_invalid.append(location)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("test_"):
                found_test_function = True
            else:
                top_level_helpers.append(location)
        if _is_test_case_list_assignment(node):
            test_case_lists.append(location)
        if found_test_function and _is_private_assignment(node):
            private_after_test.append(location)
    return PytestModuleFacts(
        empty_or_docstring_only=not module.body
        or (len(module.body) == 1 and _is_docstring_statement(module.body[0])),
        scenario_invalid_locations=tuple(scenario_invalid),
        top_level_helper_locations=tuple(top_level_helpers),
        test_case_list_locations=tuple(test_case_lists),
        private_after_test_locations=tuple(private_after_test),
    )


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _has_dataclass_decorator(node: ast.ClassDef) -> bool:
    return any(
        _decorator_name(decorator).endswith(_dataclass_decorator_name)
        for decorator in node.decorator_list
    )


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _is_test_case_list_assignment(node: ast.stmt) -> bool:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return _is_case_list_name(node.target.id)
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and _is_case_list_name(target.id)
            for target in node.targets
        )
    return False


def _is_case_list_name(name: str) -> bool:
    return name == _test_case_list_name or name.endswith(_test_case_list_suffix)


def _is_private_assignment(node: ast.stmt) -> bool:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id.startswith("_")
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id.startswith("_") for target in node.targets
        )
    return False
