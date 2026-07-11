"""Rule check functions for the shape family."""

from __future__ import annotations

import ast
import os
from functools import lru_cache
from pathlib import Path

from strata.discovery.core.types import RoleName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext, Threshold

_no_return_annotation_names: frozenset[str] = frozenset({"Never", "NoReturn", "None"})
_module_separator: str = "."


def too_many_statements(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions exceeding the tight statement threshold."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_STATEMENTS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().top_level:
        count: int = fact.statement_count
        if count > limit:
            faults.append(ctx.fault_at(fact.location, message=f"function has {count} statements"))
    return faults


def too_many_distinct_calls(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions with too many distinct callees."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_DISTINCT_CALLS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().top_level:
        count: int = fact.distinct_call_count
        if count > limit:
            faults.append(
                ctx.fault_at(fact.location, message=f"function calls {count} distinct functions")
            )
    return faults


def too_many_locals(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main/ top-level functions juggling too many local variables."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(Threshold.MAX_LOCALS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().top_level:
        count: int = fact.assigned_local_count
        if count > limit:
            faults.append(
                ctx.fault_at(fact.location, message=f"function defines {count} local variables")
            )
    return faults


def max_arguments(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag functions exceeding the configured argument limit."""

    del module
    limit: int = ctx.threshold(Threshold.MAX_ARGUMENTS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().functions:
        count: int = fact.parameter_count
        if count > limit:
            faults.append(ctx.fault_at(fact.location, message=f"function has {count} parameters"))
    return faults


def max_statements_global(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag any function exceeding the loose global statement threshold."""

    del module
    limit: int = ctx.threshold(Threshold.MAX_STATEMENTS_GLOBAL)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().functions:
        count: int = fact.statement_count
        if count > limit:
            faults.append(ctx.fault_at(fact.location, message=f"function has {count} statements"))
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

    del module
    limit: int = ctx.threshold(Threshold.MAX_POSITIONAL_ARGS)
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.functions().functions:
        if fact.dunder:
            continue
        count: int = fact.positional_parameter_count
        if count > limit:
            faults.append(
                ctx.fault_at(fact.location, message=f"function has {count} positional parameters")
            )
    return faults


def no_outer_state_mutation(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag function mutations of module-global or closure-captured state."""

    del module
    return [ctx.fault_at(fact.location) for fact in ctx._analysis.facts.outer_state_mutations()]


def no_complex_comprehensions(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag comprehensions that combine generators or nest another comprehension."""

    del module
    return [ctx.fault_at(location) for location in ctx._analysis.facts.complex_comprehensions()]


def mutable_result_model(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag dataclass result models that are not frozen."""

    del module
    if ctx.role_of() != RoleName.MODELS:
        return []
    return [
        ctx.fault_at(fact.location)
        for fact in ctx._analysis.facts.dataclasses()
        if fact.shape_candidate and not fact.frozen
    ]


def _parameter_mutation_faults(
    *, module: ast.Module, ctx: RuleContext, require_return: bool
) -> list[Fault]:
    del module
    return [
        ctx.fault_at(fact.location)
        for fact in ctx._analysis.facts.parameter_mutations()
        if not fact.dunder and not fact.setter and (not require_return or not fact.returned)
    ]


def _top_level_function_nodes(
    module: ast.Module,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    return tuple(
        node
        for node in _non_docstring_body(module)
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


def _bare_calls(
    *, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> tuple[tuple[ast.Expr, ast.Call], ...]:
    calls: list[tuple[ast.Expr, ast.Call]] = []
    for statement in function_node.body:
        calls.extend(_bare_calls_in_node(node=statement))
    return tuple(calls)


def _bare_calls_in_node(*, node: ast.AST) -> tuple[tuple[ast.Expr, ast.Call], ...]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        return ()
    if isinstance(node, ast.Expr):
        call: ast.Call | None = _expression_call(node.value)
        if call is not None:
            return ((node, call),)
    calls: list[tuple[ast.Expr, ast.Call]] = []
    for child in ast.iter_child_nodes(node):
        calls.extend(_bare_calls_in_node(node=child))
    return tuple(calls)


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
        file_stat: os.stat_result = module_path.stat()
        imported_module: ast.Module | None = _project_module(
            path=module_path,
            modified_ns=file_stat.st_mtime_ns,
            changed_ns=file_stat.st_ctime_ns,
            size=file_stat.st_size,
        )
    except OSError:
        return None
    if imported_module is None:
        return None
    return _module_function(module=imported_module, name=symbol)


@lru_cache(maxsize=512)
def _project_module(
    *, path: Path, modified_ns: int, changed_ns: int, size: int
) -> ast.Module | None:
    del modified_ns, changed_ns, size
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return None


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
            if alias.asname is None and _module_separator in alias.name:
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
