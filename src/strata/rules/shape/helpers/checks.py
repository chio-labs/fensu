"""Rule check functions for the shape family."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext, Threshold

_mutator_methods: frozenset[str] = frozenset(
    {"add", "append", "clear", "extend", "insert", "pop", "remove", "setdefault", "update"}
)
_exempt_parameters: frozenset[str] = frozenset({"cls", "self"})
_no_return_annotation_names: frozenset[str] = frozenset({"Never", "NoReturn", "None"})


def too_many_statements(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
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


def too_many_distinct_calls(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
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


def too_many_locals(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
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


def max_arguments(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag functions exceeding the configured argument limit."""

    limit: int = ctx.threshold(Threshold.MAX_ARGUMENTS)
    faults: list[Fault] = []
    for function_node in _function_nodes(module):
        count: int = len(_parameter_names(function_node))
        if count > limit:
            faults.append(ctx.fault(function_node, message=f"function has {count} parameters"))
    return faults


def max_statements_global(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag any function exceeding the loose global statement threshold."""

    limit: int = ctx.threshold(Threshold.MAX_STATEMENTS_GLOBAL)
    faults: list[Fault] = []
    for function_node in _function_nodes(module):
        count: int = _statement_count(function_node)
        if count > limit:
            faults.append(ctx.fault(function_node, message=f"function has {count} statements"))
    return faults


def meaningful_project_result_discarded(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag discarded meaningful results from resolved project-local calls."""

    if not ctx.is_main_module():
        return []
    faults: list[Fault] = []
    for function_node in _top_level_function_nodes(module):
        for statement, call in _bare_calls(function_node=function_node):
            resolved_function: ast.FunctionDef | ast.AsyncFunctionDef | None = (
                _resolve_project_function(
                    call=call,
                    module=module,
                    function_node=function_node,
                    ctx=ctx,
                    repo_root=ctx.repo_root,
                )
            )
            if resolved_function is not None and _has_meaningful_return(resolved_function):
                faults.append(ctx.fault(statement))
    return faults


def parameter_mutation_in_phase_helpers(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag direct parameter mutation in helper functions."""

    if not ctx.in_role("helpers"):
        return []
    return _parameter_mutation_faults(module=module, ctx=ctx, require_return=False)


def default_mutation_return(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag parameter mutation unless all mutated parameters are returned."""

    return _parameter_mutation_faults(module=module, ctx=ctx, require_return=True)


def keyword_only_arguments(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
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


def mutable_result_model(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
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


def _bare_calls(
    *, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> tuple[tuple[ast.Expr, ast.Call], ...]:
    return tuple(
        call for statement in function_node.body for call in _bare_calls_in_node(node=statement)
    )


def _bare_calls_in_node(*, node: ast.AST) -> tuple[tuple[ast.Expr, ast.Call], ...]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        return ()
    if isinstance(node, ast.Expr):
        call: ast.Call | None = _expression_call(node.value)
        if call is not None:
            return ((node, call),)
    return tuple(
        call for child in ast.iter_child_nodes(node) for call in _bare_calls_in_node(node=child)
    )


def _expression_call(node: ast.expr) -> ast.Call | None:
    if isinstance(node, ast.Call):
        return node
    if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
        return node.value
    return None


def _resolve_project_function(
    *,
    call: ast.Call,
    module: ast.Module,
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ctx: RuleContext,
    repo_root: Path,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    if isinstance(call.func, ast.Name):
        if call.func.id in ctx.parameter_names(function_node) | ctx.assigned_locals(function_node):
            return None
        local_function: ast.FunctionDef | ast.AsyncFunctionDef | None = _module_function(
            module=module, name=call.func.id
        )
        if local_function is not None:
            return local_function
        imported_symbol: tuple[str, str] | None = _imported_symbol(
            module=module, local_name=call.func.id
        )
        if imported_symbol is None:
            return None
        return _resolve_imported_function(
            module_name=imported_symbol[0], symbol=imported_symbol[1], repo_root=repo_root
        )
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        module_name: str | None = _imported_module(module=module, local_name=call.func.value.id)
        if module_name is not None:
            return _resolve_imported_function(
                module_name=module_name, symbol=call.func.attr, repo_root=repo_root
            )
    return None


def _resolve_imported_function(
    *, module_name: str, symbol: str, repo_root: Path
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    module_path: Path | None = _project_module_path(module_name=module_name, repo_root=repo_root)
    if module_path is None:
        return None
    try:
        imported_module: ast.Module = ast.parse(module_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return None
    return _module_function(module=imported_module, name=symbol)


def _project_module_path(*, module_name: str, repo_root: Path) -> Path | None:
    relative_path: Path = Path(*module_name.split("."))
    for source_root in (repo_root / "src", repo_root):
        module_path: Path = source_root / relative_path.with_suffix(".py")
        if module_path.is_file():
            return module_path
        package_path: Path = source_root / relative_path / "__init__.py"
        if package_path.is_file():
            return package_path
    return None


def _module_function(
    *, module: ast.Module, name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name
        ),
        None,
    )


def _imported_symbol(*, module: ast.Module, local_name: str) -> tuple[str, str] | None:
    for node in module.body:
        if not isinstance(node, ast.ImportFrom) or node.level or node.module is None:
            continue
        for alias in node.names:
            if (alias.asname or alias.name) == local_name:
                return node.module, alias.name
    return None


def _imported_module(*, module: ast.Module, local_name: str) -> str | None:
    for node in module.body:
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.asname is None and "." in alias.name:
                continue
            bound_name: str = alias.asname or alias.name
            if bound_name == local_name:
                return alias.name
    return None


def _has_meaningful_return(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    annotation: ast.expr | None = function_node.returns
    if annotation is None or (isinstance(annotation, ast.Constant) and annotation.value is None):
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id not in _no_return_annotation_names
    if isinstance(annotation, ast.Attribute):
        return annotation.attr not in _no_return_annotation_names
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value.rsplit(".", maxsplit=1)[-1] not in _no_return_annotation_names
    return True


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
