"""Import and attribute-reference fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis._helpers.locations import source_location
from strata.analysis.models import (
    AssignmentReferenceFact,
    AttributeReferenceFact,
    ComparisonFact,
    DefinitionIdentity,
    ImportAliasFact,
    ImportFact,
    LiteralArgumentFact,
    LocalCallEdgeFact,
    NamedCallFact,
    PytestModuleFacts,
    QualifiedReferenceFact,
    ReferenceFacts,
    SourceLocation,
)

_test_case_list_name: str = "TEST_CASES"
_test_case_list_suffix: str = "_TEST_CASES"
_dataclass_decorator_name: str = "dataclass"
_super_call_name: str = "super"


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


def assignment_reference_facts(
    *,
    path: Path,
    nodes: tuple[ast.AST, ...],
    parent_by_node: Mapping[ast.AST, ast.AST],
) -> tuple[AssignmentReferenceFact, ...]:
    """Return assignment ownership, targets, and strict RHS references in BFS order."""

    facts: list[AssignmentReferenceFact] = []
    for node in nodes:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        targets: tuple[ast.expr, ...] = (
            tuple(node.targets) if isinstance(node, ast.Assign) else (node.target,)
        )
        target_names: list[str] = []
        for target in targets:
            target_names.extend(_stored_target_names(target))
        value: ast.expr | None = node.value
        value_reference: QualifiedReferenceFact | None = None
        if isinstance(value, ast.Name | ast.Attribute) and _strict_reference_parts(value):
            value_reference = _qualified_reference(value)
        classes: tuple[DefinitionIdentity, ...] = _enclosing_identities(
            path=path,
            node=node,
            parent_by_node=parent_by_node,
            definition_types=(ast.ClassDef,),
        )
        functions: tuple[DefinitionIdentity, ...] = _enclosing_identities(
            path=path,
            node=node,
            parent_by_node=parent_by_node,
            definition_types=(ast.FunctionDef, ast.AsyncFunctionDef),
        )
        facts.append(
            AssignmentReferenceFact(
                location=source_location(path=path, node=node),
                owning_class=classes[0] if classes else None,
                owning_function=functions[0] if functions else None,
                target_names=tuple(target_names),
                value_reference=value_reference,
            )
        )
    return tuple(facts)


def named_call_facts(
    *,
    path: Path,
    nodes: tuple[ast.AST, ...],
    parent_by_node: Mapping[ast.AST, ast.AST],
) -> tuple[NamedCallFact, ...]:
    """Return all calls in BFS order with nearest-first lexical owners."""

    facts: list[NamedCallFact] = []
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        reference: QualifiedReferenceFact = _qualified_reference(node.func)
        classes: tuple[DefinitionIdentity, ...] = _enclosing_identities(
            path=path,
            node=node,
            parent_by_node=parent_by_node,
            definition_types=(ast.ClassDef,),
        )
        functions: tuple[DefinitionIdentity, ...] = _enclosing_identities(
            path=path,
            node=node,
            parent_by_node=parent_by_node,
            definition_types=(ast.FunctionDef, ast.AsyncFunctionDef),
        )
        ancestors: tuple[ast.AST, ...] = _ancestor_nodes(node=node, parent_by_node=parent_by_node)
        parent: ast.AST | None = parent_by_node.get(node)
        facts.append(
            NamedCallFact(
                location=source_location(path=path, node=node),
                name=reference.name,
                reference=reference,
                owning_class=classes[0] if classes else None,
                owning_function=functions[0] if functions else None,
                enclosing_classes=classes,
                enclosing_functions=functions,
                inside_loop=_has_loop_ancestor(ancestors),
                literal_arguments=_literal_arguments(node),
                bare_expression=isinstance(parent, ast.Expr) and parent.value is node,
                super_call=isinstance(node.func, ast.Name) and node.func.id == _super_call_name,
            )
        )
    return tuple(facts)


def local_call_edge_facts(
    *,
    path: Path,
    nodes: tuple[ast.AST, ...],
    parent_by_node: Mapping[ast.AST, ast.AST],
) -> tuple[LocalCallEdgeFact, ...]:
    """Return one edge per call and enclosing named function, nearest caller first."""

    facts: list[LocalCallEdgeFact] = []
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        ancestors: tuple[ast.AST, ...] = _ancestor_nodes(node=node, parent_by_node=parent_by_node)
        inside_loop: bool = _has_loop_ancestor(ancestors)
        callee: QualifiedReferenceFact = _qualified_reference(node.func)
        for caller_node in ancestors:
            if not isinstance(caller_node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            caller_classes: tuple[DefinitionIdentity, ...] = _enclosing_identities(
                path=path,
                node=caller_node,
                parent_by_node=parent_by_node,
                definition_types=(ast.ClassDef,),
            )
            facts.append(
                LocalCallEdgeFact(
                    location=source_location(path=path, node=node),
                    caller=_definition_identity(path=path, node=caller_node),
                    caller_class=caller_classes[0] if caller_classes else None,
                    callee=callee,
                    inside_loop=inside_loop,
                )
            )
    return tuple(facts)


def comparison_facts(*, path: Path, nodes: tuple[ast.AST, ...]) -> tuple[ComparisonFact, ...]:
    """Return comparisons with references aligned to direct operand positions."""

    facts: list[ComparisonFact] = []
    for node in nodes:
        if not isinstance(node, ast.Compare):
            continue
        operands: tuple[ast.expr, ...] = (node.left, *node.comparators)
        references: list[QualifiedReferenceFact | None] = []
        for operand in operands:
            references.append(
                _qualified_reference(operand)
                if isinstance(operand, ast.Name | ast.Attribute | ast.Subscript)
                else None
            )
        facts.append(
            ComparisonFact(
                location=source_location(path=path, node=node),
                operand_references=tuple(references),
            )
        )
    return tuple(facts)


def _definition_identity(
    *, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
) -> DefinitionIdentity:
    return DefinitionIdentity(name=node.name, location=source_location(path=path, node=node))


def _enclosing_identities(
    *,
    path: Path,
    node: ast.AST,
    parent_by_node: Mapping[ast.AST, ast.AST],
    definition_types: tuple[type[ast.AST], ...],
) -> tuple[DefinitionIdentity, ...]:
    identities: list[DefinitionIdentity] = []
    for ancestor in _ancestor_nodes(node=node, parent_by_node=parent_by_node):
        if isinstance(ancestor, definition_types) and isinstance(
            ancestor, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            identities.append(_definition_identity(path=path, node=ancestor))
    return tuple(identities)


def _ancestor_nodes(
    *, node: ast.AST, parent_by_node: Mapping[ast.AST, ast.AST]
) -> tuple[ast.AST, ...]:
    ancestors: list[ast.AST] = []
    current: ast.AST | None = parent_by_node.get(node)
    while current is not None:
        ancestors.append(current)
        current = parent_by_node.get(current)
    return tuple(ancestors)


def _stored_target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,) if isinstance(node.ctx, ast.Store) else ()
    names: list[str] = []
    for child in ast.iter_child_nodes(node):
        names.extend(_stored_target_names(child))
    return tuple(names)


def _qualified_reference(node: ast.expr) -> QualifiedReferenceFact:
    if isinstance(node, ast.Name):
        kind: str = "name"
    elif isinstance(node, ast.Attribute):
        kind = "attribute"
    elif isinstance(node, ast.Subscript):
        kind = "subscript"
    else:
        kind = "other"
    return QualifiedReferenceFact(
        kind=kind,
        name=_lenient_reference_name(node),
        base_name=_reference_base_name(node),
        receiver_base_name=(
            _reference_base_name(node.value) if isinstance(node, ast.Attribute) else None
        ),
        parts=_strict_reference_parts(node),
    )


def _lenient_reference_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str | None = _lenient_reference_name(node.value)
        return node.attr if parent is None else f"{parent}.{node.attr}"
    return None


def _reference_base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _reference_base_name(node.value)
    return None


def _strict_reference_parts(node: ast.expr) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        parent: tuple[str, ...] = _strict_reference_parts(node.value)
        return (*parent, node.attr) if parent else ()
    if isinstance(node, ast.Subscript):
        return _strict_reference_parts(node.value)
    return ()


def _literal_arguments(node: ast.Call) -> tuple[LiteralArgumentFact, ...]:
    arguments: list[LiteralArgumentFact] = []
    for position, argument in enumerate(node.args):
        if not isinstance(argument, ast.Constant):
            continue
        fact: LiteralArgumentFact | None = _literal_argument(position=position, node=argument)
        if fact is not None:
            arguments.append(fact)
    return tuple(arguments)


def _literal_argument(*, position: int, node: ast.Constant) -> LiteralArgumentFact | None:
    value: object = node.value
    kind: str
    literal_value: str | bytes | int | float | complex | bool | None
    if value is Ellipsis:
        kind = "ellipsis"
        literal_value = None
    elif value is None:
        kind = "none"
        literal_value = None
    elif isinstance(value, bool):
        kind = "boolean"
        literal_value = value
    elif isinstance(value, str):
        kind = "string"
        literal_value = value
    elif isinstance(value, bytes):
        kind = "bytes"
        literal_value = value
    elif isinstance(value, int):
        kind = "integer"
        literal_value = value
    elif isinstance(value, float):
        kind = "float"
        literal_value = value
    elif isinstance(value, complex):
        kind = "complex"
        literal_value = value
    else:
        return None
    return LiteralArgumentFact(position=position, kind=kind, value=literal_value)


def _has_loop_ancestor(ancestors: tuple[ast.AST, ...]) -> bool:
    return any(isinstance(node, ast.For | ast.AsyncFor | ast.While) for node in ancestors)


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
