"""Rule check functions for the shape family."""

from __future__ import annotations

import ast

from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext, Threshold

_mutator_methods: frozenset[str] = frozenset(
    {"add", "append", "clear", "extend", "insert", "pop", "remove", "setdefault", "update"}
)
_exempt_parameters: frozenset[str] = frozenset({"cls", "self"})
_discarded_call_allowed_names: frozenset[str] = frozenset({"print"})
_discarded_call_allowed_prefixes: tuple[str, ...] = (
    "check_",
    "enforce_",
    "validate_",
    "on_",
    "report_",
    "log",
    "write_",
)


def too_many_statements(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions exceeding the tight statement threshold."""

    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_STATEMENTS)
    faults: list[Fault] = []
    for function_node in _top_level_function_nodes(module):
        count: int = _statement_count(function_node)
        if count > limit:
            faults.append(ctx.fault(function_node, message=f"function has {count} statements"))
    return faults


def too_many_distinct_calls(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions with too many distinct callees."""

    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_DISTINCT_CALLS)
    faults: list[Fault] = []
    for function_node in _top_level_function_nodes(module):
        count: int = len(ctx.distinct_callees(function_node))
        if count > limit:
            faults.append(
                ctx.fault(function_node, message=f"function calls {count} distinct functions")
            )
    return faults


def too_many_locals(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions juggling too many local variables."""

    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_LOCALS)
    faults: list[Fault] = []
    for function_node in _top_level_function_nodes(module):
        count: int = len(_assigned_local_names(function_node))
        if count > limit:
            faults.append(
                ctx.fault(function_node, message=f"function defines {count} local variables")
            )
    return faults


def max_arguments(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag functions exceeding the configured argument limit."""

    limit: int = ctx.threshold(Threshold.MAX_ARGUMENTS)
    faults: list[Fault] = []
    for function_node in _function_nodes(module):
        count: int = len(_parameter_names(function_node))
        if count > limit:
            faults.append(ctx.fault(function_node, message=f"function has {count} parameters"))
    return faults


def max_statements_global(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag any function exceeding the loose global statement threshold."""

    limit: int = ctx.threshold(Threshold.MAX_STATEMENTS_GLOBAL)
    faults: list[Fault] = []
    for function_node in _function_nodes(module):
        count: int = _statement_count(function_node)
        if count > limit:
            faults.append(ctx.fault(function_node, message=f"function has {count} statements"))
    return faults


def discarded_call_result(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ orchestrator bare calls whose result is discarded."""

    if not ctx.is_main_module():
        return []
    faults: list[Fault] = []
    for function_node in _top_level_function_nodes(module):
        for node in ast.walk(function_node):
            if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
                continue
            if _discarded_call_is_allowed(node.value):
                continue
            faults.append(ctx.fault(node))
    return faults


def parameter_mutation_in_phase_helpers(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag direct parameter mutation in helper functions."""

    if not ctx.in_role("helpers"):
        return []
    return _parameter_mutation_faults(module=module, ctx=ctx, require_return=False)


def default_mutation_return(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag parameter mutation unless all mutated parameters are returned."""

    return _parameter_mutation_faults(module=module, ctx=ctx, require_return=True)


def keyword_only_arguments(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag excess positional parameters that should be keyword-only."""

    limit: int = ctx.threshold(Threshold.MAX_POSITIONAL_ARGS)
    faults: list[Fault] = []
    for function_node in _function_nodes(module):
        if _function_is_dunder(function_node):
            continue
        count: int = len(
            [
                arg.arg
                for arg in (*function_node.args.posonlyargs, *function_node.args.args)
                if arg.arg not in _exempt_parameters
            ]
        )
        if count > limit:
            faults.append(
                ctx.fault(function_node, message=f"function has {count} positional parameters")
            )
    return faults


def mutable_result_model(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag dataclass result models that are not frozen."""

    if ctx.role_of() != "models":
        return []
    faults: list[Fault] = []
    for node in module.body:
        if isinstance(node, ast.ClassDef) and _is_mutable_dataclass(node):
            faults.append(ctx.fault(node))
    return faults


def _parameter_mutation_faults(
    *, module: ast.Module, ctx: RuleContext, require_return: bool
) -> list[Fault]:
    faults: list[Fault] = []
    for function_node in _function_nodes(module):
        if _function_is_exempt_from_mutation_return(function_node):
            continue
        parameter_names: frozenset[str] = _parameter_names(function_node)
        mutated_names: dict[str, ast.AST] = {}
        for node in ast.walk(function_node):
            mutated_name: str | None = _parameter_mutated_by_node(
                node=node, parameter_names=parameter_names
            )
            if mutated_name is not None:
                mutated_names.setdefault(mutated_name, node)
        if not mutated_names:
            continue
        if require_return:
            returned_names: frozenset[str] = _returned_names(function_node)
            mutated_names = {
                name: node for name, node in mutated_names.items() if name not in returned_names
            }
            if not mutated_names:
                continue
        faults.extend(ctx.fault(node) for node in mutated_names.values())
    return faults


def _top_level_function_nodes(
    module: ast.Module,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    return tuple(
        node
        for node in _non_docstring_body(module)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )


def _function_nodes(module: ast.Module) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    return tuple(
        node
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )


def _non_docstring_body(module: ast.Module) -> tuple[ast.stmt, ...]:
    if len(module.body) == 0:
        return ()
    first_statement: ast.stmt = module.body[0]
    if (
        isinstance(first_statement, ast.Expr)
        and isinstance(first_statement.value, ast.Constant)
        and isinstance(first_statement.value.value, str)
    ):
        return tuple(module.body[1:])
    return tuple(module.body)


def _statement_count(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return sum(1 for node in ast.walk(function_node) if isinstance(node, ast.stmt)) - 1


def _assigned_local_names(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(function_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return frozenset(names)


def _parameter_names(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    args: ast.arguments = function_node.args
    names: set[str] = {
        arg.arg
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)
        if arg.arg not in _exempt_parameters
    }
    if args.vararg is not None and args.vararg.arg not in _exempt_parameters:
        names.add(args.vararg.arg)
    if args.kwarg is not None and args.kwarg.arg not in _exempt_parameters:
        names.add(args.kwarg.arg)
    return frozenset(names)


def _discarded_call_is_allowed(node: ast.Call) -> bool:
    name: str | None = _call_name(node)
    if name is None:
        return True
    bare_name: str = name.rsplit(".", maxsplit=1)[-1].lstrip("_")
    return bare_name in _discarded_call_allowed_names or bare_name.startswith(
        _discarded_call_allowed_prefixes
    )


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _parameter_mutated_by_node(*, node: ast.AST, parameter_names: frozenset[str]) -> str | None:
    if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
        return _parameter_mutated_by_assignment(node=node, parameter_names=parameter_names)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr not in _mutator_methods:
            return None
        return _root_parameter_name(node=node.func.value, parameter_names=parameter_names)
    return None


def _parameter_mutated_by_assignment(
    *, node: ast.Assign | ast.AnnAssign | ast.AugAssign, parameter_names: frozenset[str]
) -> str | None:
    targets: tuple[ast.expr, ...]
    if isinstance(node, ast.Assign):
        targets = tuple(node.targets)
    else:
        targets = (node.target,)
    for target in targets:
        parameter_name: str | None = _root_parameter_name(
            node=target, parameter_names=parameter_names
        )
        if parameter_name is not None and not isinstance(target, ast.Name):
            return parameter_name
    return None


def _root_parameter_name(*, node: ast.AST, parameter_names: frozenset[str]) -> str | None:
    if isinstance(node, ast.Name):
        return node.id if node.id in parameter_names else None
    if isinstance(node, ast.Attribute):
        return _root_parameter_name(node=node.value, parameter_names=parameter_names)
    if isinstance(node, ast.Subscript):
        return _root_parameter_name(node=node.value, parameter_names=parameter_names)
    return None


def _returned_names(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(function_node):
        if isinstance(node, ast.Return) and node.value is not None:
            names.update(_names_in_expr(node.value))
    return frozenset(names)


def _names_in_expr(node: ast.AST) -> frozenset[str]:
    return frozenset(child.id for child in ast.walk(node) if isinstance(child, ast.Name))


def _function_is_exempt_from_mutation_return(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    if _function_is_dunder(function_node):
        return True
    return any(
        _decorator_name(decorator).endswith(".setter") for decorator in function_node.decorator_list
    )


def _function_is_dunder(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return function_node.name.startswith("__") and function_node.name.endswith("__")


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _is_mutable_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and _decorator_name(decorator.func) == "dataclass":
            return not _dataclass_call_is_frozen(decorator)
        if _decorator_name(decorator) == "dataclass":
            return True
    return False


def _dataclass_call_is_frozen(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "frozen" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value is True
    return False
