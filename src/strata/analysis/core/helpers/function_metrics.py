"""Shared structural function-metric extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.locations import source_location
from strata.analysis.core.models import (
    DataclassFact,
    FunctionFacts,
    FunctionMetricFact,
    ParametrizeCaseFact,
    ParametrizeFact,
    PytestFunctionFact,
    SourceLocation,
)

_exempt_parameters: frozenset[str] = frozenset({"cls", "self"})
_dataclass_decorator_name: str = "dataclass"
_frozen_keyword_name: str = "frozen"
_parametrize_decorator_name: str = "pytest.mark.parametrize"
_test_case_name: str = "test_case"
_case_name: str = "case"
_description_name: str = "description"
_ids_keyword_name: str = "ids"
_minimum_parametrize_arguments: int = 2
_minimum_expected_field_chain_parts: int = 2


def function_facts(
    *,
    path: Path,
    module: ast.Module,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> FunctionFacts:
    """Return shared metrics for all functions and top-level functions."""

    function_nodes: tuple[ast.AST, ...] = (
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
    )
    if not function_nodes:
        return FunctionFacts(functions=(), top_level=())
    fact_by_node: dict[ast.AST, FunctionMetricFact] = {}
    functions: list[FunctionMetricFact] = []
    for node in function_nodes:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        fact: FunctionMetricFact = _function_metric_fact(path=path, node=node)
        fact_by_node[node] = fact
        functions.append(fact)
    top_level: tuple[FunctionMetricFact, ...] = tuple(
        fact_by_node[node]
        for node in module.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    return FunctionFacts(functions=tuple(functions), top_level=top_level)


def _function_metric_fact(
    *,
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> FunctionMetricFact:
    statement_count: int = -1
    call_names: set[str] = set()
    assigned_names: set[str] = set()
    for descendant in ast.walk(node):
        if isinstance(descendant, ast.stmt):
            statement_count += 1
        if isinstance(descendant, ast.Call):
            call_name: str | None = _call_name(descendant)
            if call_name is not None:
                call_names.add(call_name)
        if isinstance(descendant, ast.Assign):
            for target in descendant.targets:
                if isinstance(target, ast.Name):
                    assigned_names.add(target.id)
        if isinstance(descendant, ast.AnnAssign) and isinstance(descendant.target, ast.Name):
            assigned_names.add(descendant.target.id)
    parameter_names: frozenset[str] = _parameter_names(node)
    positional_parameter_count: int = len(
        [
            argument
            for argument in (*node.args.posonlyargs, *node.args.args)
            if argument.arg not in _exempt_parameters
        ]
    )
    return FunctionMetricFact(
        location=source_location(path=path, node=node),
        name=node.name,
        statement_count=statement_count,
        distinct_call_count=len(call_names),
        assigned_local_count=len(assigned_names),
        parameter_count=len(parameter_names),
        positional_parameter_count=positional_parameter_count,
        dunder=node.name.startswith("__") and node.name.endswith("__"),
    )


def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    arguments: ast.arguments = node.args
    names: set[str] = {
        argument.arg
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
        if argument.arg not in _exempt_parameters
    }
    if arguments.vararg is not None and arguments.vararg.arg not in _exempt_parameters:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None and arguments.kwarg.arg not in _exempt_parameters:
        names.add(arguments.kwarg.arg)
    return frozenset(names)


def _call_name(node: ast.Call) -> str | None:
    return _name_from_expr(node.func)


def _name_from_expr(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base: str | None = _name_from_expr(node.value)
        return node.attr if base is None else f"{base}.{node.attr}"
    return None


def dataclass_facts(*, path: Path, module: ast.Module) -> tuple[DataclassFact, ...]:
    """Return top-level dataclass declarations and field metadata."""

    facts: list[DataclassFact] = []
    for node in module.body:
        if not isinstance(node, ast.ClassDef):
            continue
        decorator: ast.expr | None = next(
            (
                candidate
                for candidate in node.decorator_list
                if _decorator_name(candidate).endswith(_dataclass_decorator_name)
            ),
            None,
        )
        if decorator is None:
            continue
        decorator_name: str = _decorator_name(
            decorator.func if isinstance(decorator, ast.Call) else decorator
        )
        facts.append(
            DataclassFact(
                name=node.name,
                location=source_location(path=path, node=node),
                field_names=frozenset(
                    statement.target.id
                    for statement in node.body
                    if isinstance(statement, ast.AnnAssign)
                    and isinstance(statement.target, ast.Name)
                ),
                frozen=_dataclass_call_is_frozen(decorator),
                shape_candidate=decorator_name == _dataclass_decorator_name,
            )
        )
    return tuple(facts)


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _dataclass_call_is_frozen(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    for keyword in node.keywords:
        if keyword.arg == _frozen_keyword_name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value is True
    return False


def test_function_facts(
    *,
    path: Path,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> tuple[PytestFunctionFact, ...]:
    """Return reusable syntax metadata for test functions."""

    facts: list[PytestFunctionFact] = []
    nodes: tuple[ast.AST, ...] = (
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
    )
    for node in nodes:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or not node.name.startswith(
            "test_"
        ):
            continue
        test_case_argument: ast.arg | None = next(
            (argument for argument in node.args.args if argument.arg == _test_case_name),
            None,
        )
        references_expected_field, conditional_locations = _test_body_metadata(
            path=path,
            node=node,
        )
        facts.append(
            PytestFunctionFact(
                name=node.name,
                location=source_location(path=path, node=node),
                parameter_names=frozenset(argument.arg for argument in node.args.args),
                test_case_annotation_name=(
                    test_case_argument.annotation.id
                    if test_case_argument is not None
                    and isinstance(test_case_argument.annotation, ast.Name)
                    else None
                ),
                parametrize=_parametrize_fact(path=path, node=node),
                references_expected_field=references_expected_field,
                conditional_locations=conditional_locations,
            )
        )
    return tuple(facts)


def _parametrize_fact(
    *, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> ParametrizeFact | None:
    decorator: ast.Call | None = next(
        (
            candidate
            for candidate in node.decorator_list
            if isinstance(candidate, ast.Call)
            and _decorator_name(candidate.func) == _parametrize_decorator_name
        ),
        None,
    )
    if decorator is None:
        return None
    ids_expression: ast.expr | None = next(
        (keyword.value for keyword in decorator.keywords if keyword.arg == _ids_keyword_name),
        None,
    )
    if len(decorator.args) < _minimum_parametrize_arguments:
        return ParametrizeFact(
            argument_count=len(decorator.args),
            parameter_name=_extract_string(decorator.args[0]) if decorator.args else None,
            ids_present=ids_expression is not None,
            description_lambda_ids=_is_description_lambda_ids(ids_expression),
            values_is_name=False,
            values_is_list_comprehension=False,
            values_is_sequence=False,
            values_empty=False,
            cases=(),
        )
    values_expression: ast.expr = decorator.args[1]
    case_nodes: tuple[ast.expr, ...] = ()
    if isinstance(values_expression, ast.ListComp):
        case_nodes = (values_expression.elt,)
    elif isinstance(values_expression, ast.List | ast.Tuple):
        case_nodes = tuple(values_expression.elts)
    return ParametrizeFact(
        argument_count=len(decorator.args),
        parameter_name=_extract_string(decorator.args[0]),
        ids_present=ids_expression is not None,
        description_lambda_ids=_is_description_lambda_ids(ids_expression),
        values_is_name=isinstance(values_expression, ast.Name),
        values_is_list_comprehension=isinstance(values_expression, ast.ListComp),
        values_is_sequence=isinstance(values_expression, ast.List | ast.Tuple),
        values_empty=isinstance(values_expression, ast.List | ast.Tuple)
        and not values_expression.elts,
        cases=tuple(_parametrize_case(path=path, node=case) for case in case_nodes),
    )


def _parametrize_case(*, path: Path, node: ast.expr) -> ParametrizeCaseFact:
    constructor_name: str | None = None
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        constructor_name = node.func.id
    return ParametrizeCaseFact(
        location=source_location(path=path, node=node),
        constructor_name=constructor_name,
        dictionary=isinstance(node, ast.Dict),
    )


def _extract_string(node: ast.expr) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _is_description_lambda_ids(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Lambda)
        and len(node.args.args) == 1
        and node.args.args[0].arg == _case_name
        and _attribute_chain(node.body) == (_case_name, _description_name)
    )


def _test_body_metadata(
    *, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> tuple[bool, tuple[SourceLocation, ...]]:
    references_expected_field: bool = False
    conditional_locations: list[SourceLocation] = []
    for descendant in ast.walk(node):
        if isinstance(descendant, ast.Attribute):
            chain: tuple[str, ...] | None = _attribute_chain(descendant)
            if (
                chain
                and len(chain) >= _minimum_expected_field_chain_parts
                and chain[0] == _test_case_name
                and chain[-1].startswith("expected_")
            ):
                references_expected_field = True
        if isinstance(descendant, ast.If | ast.IfExp | ast.Match | ast.While):
            conditional_locations.append(source_location(path=path, node=descendant))
        elif isinstance(descendant, ast.comprehension):
            conditional_locations.extend(
                source_location(path=path, node=condition) for condition in descendant.ifs
            )
    return references_expected_field, tuple(conditional_locations)


def _attribute_chain(node: ast.expr) -> tuple[str, ...] | None:
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return tuple(reversed(parts))
    return None
