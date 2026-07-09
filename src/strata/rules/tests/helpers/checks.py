"""Rule check functions for the tests family."""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext
from strata.rules.tests.types import SftCode

_test_name_pattern: re.Pattern[str] = re.compile(r"^test_given_.+_when_.+_then_.+$")
_valid_test_scopes: frozenset[str] = frozenset({"unit", "integration", "e2e"})


@dataclass(frozen=True)
class _LocalTestTypes:
    module_name: str
    dataclass_names: frozenset[str]


@dataclass(frozen=True)
class _TestModuleContext:
    imported_local_test_case_types: frozenset[str]
    test_case_annotation_names: frozenset[str]


def test_faults(*, module: ast.Module, ctx: RuleContext, code: SftCode) -> list[Fault]:
    """Collect faults for a single tests-family rule."""

    if ctx.scope() != "test":
        return []
    if ctx.path.name == "scenario_models.py" and code == SftCode.TEST_LAYOUT:
        return _scenario_models_faults(module=module, ctx=ctx)
    if code in _layout_codes():
        return _layout_faults(ctx=ctx, code=code)
    if code == SftCode.INIT_MODULE_EMPTY:
        return _init_module_faults(module=module, ctx=ctx)
    if code == SftCode.ABSOLUTE_IMPORTS:
        return _relative_import_faults(module=module, ctx=ctx)
    if ctx.path.name == "_test_types.py":
        return _test_types_faults(module=module, ctx=ctx, code=code)
    if ctx.path.name.endswith(".py"):
        return _test_file_faults(module=module, ctx=ctx, code=code)
    return []


def _layout_faults(*, ctx: RuleContext, code: SftCode) -> list[Fault]:
    if ctx.path.name in {"__init__.py", "conftest.py"}:
        return []
    try:
        relative_parts: tuple[str, ...] = (
            ctx.path.parent.resolve().relative_to(ctx.repo_root.resolve()).parts
        )
    except ValueError:
        return [_path_fault(ctx=ctx, code=SftCode.TEST_LAYOUT, message="test path is outside repo")]
    if len(relative_parts) < 3 or relative_parts[0] != "tests":
        return _selected_path_faults(
            ctx=ctx,
            code=code,
            actual_code=SftCode.TEST_LAYOUT,
            message="test directories must live under tests/<scope>/...",
        )
    scope: str = relative_parts[1]
    if scope not in _valid_test_scopes:
        return _selected_path_faults(
            ctx=ctx,
            code=code,
            actual_code=SftCode.TEST_SCOPE,
            message="test scope must be unit, integration, or e2e",
        )
    mirrored_root: str = relative_parts[2]
    if mirrored_root == "src":
        return _src_layout_faults(ctx=ctx, code=code, relative_parts=relative_parts)
    if mirrored_root == "scripts":
        return _scripts_layout_faults(ctx=ctx, code=code, relative_parts=relative_parts)
    return _selected_path_faults(
        ctx=ctx,
        code=code,
        actual_code=SftCode.TEST_MIRRORED_ROOT,
        message="test directories must mirror src or scripts",
    )


def _src_layout_faults(
    *, ctx: RuleContext, code: SftCode, relative_parts: tuple[str, ...]
) -> list[Fault]:
    if len(relative_parts) < 5:
        return _selected_path_faults(
            ctx=ctx,
            code=code,
            actual_code=SftCode.SRC_MIRROR_DEPTH,
            message="src-backed tests must live under tests/<scope>/src/<package>/<area>/...",
        )
    package_path: Path = ctx.repo_root / "src" / relative_parts[3]
    if not package_path.is_dir():
        return _selected_path_faults(
            ctx=ctx,
            code=code,
            actual_code=SftCode.SRC_PACKAGE_EXISTS,
            message="tests under tests/<scope>/src must mirror a real package under src/",
        )
    if relative_parts[3] == "strata" and relative_parts[4] == "__root__":
        return []
    area_path: Path = package_path / relative_parts[4]
    if not area_path.exists():
        return _selected_path_faults(
            ctx=ctx,
            code=code,
            actual_code=SftCode.SRC_AREA_EXISTS,
            message="tests under tests/<scope>/src must mirror a real src package area",
        )
    return []


def _scripts_layout_faults(
    *, ctx: RuleContext, code: SftCode, relative_parts: tuple[str, ...]
) -> list[Fault]:
    if len(relative_parts) < 4:
        return _selected_path_faults(
            ctx=ctx,
            code=code,
            actual_code=SftCode.SCRIPTS_MIRROR_DEPTH,
            message="script-backed tests must live under tests/<scope>/scripts/<area>/...",
        )
    area_path: Path = ctx.repo_root / "scripts" / relative_parts[3]
    if not area_path.exists():
        return _selected_path_faults(
            ctx=ctx,
            code=code,
            actual_code=SftCode.SCRIPTS_AREA_EXISTS,
            message="tests under tests/<scope>/scripts must mirror a real scripts area",
        )
    return []


def _selected_path_faults(
    *, ctx: RuleContext, code: SftCode, actual_code: SftCode, message: str
) -> list[Fault]:
    if code != actual_code:
        return []
    return [_path_fault(ctx=ctx, code=actual_code, message=message)]


def _path_fault(*, ctx: RuleContext, code: SftCode, message: str) -> Fault:
    return Fault(code=code, path=ctx.path, message=message)


def _init_module_faults(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    if ctx.path.name != "__init__.py" or _is_docstring_only_module(module):
        return []
    return [ctx.fault(module, message="__init__.py must be empty or docstring-only")]


def _relative_import_faults(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return [
        ctx.fault(node)
        for node in ctx.nodes(ast.ImportFrom)
        if isinstance(node, ast.ImportFrom) and node.level > 0
    ]


def _test_types_faults(*, module: ast.Module, ctx: RuleContext, code: SftCode) -> list[Fault]:
    faults: list[Fault] = []
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or not _has_dataclass_decorator(node):
            continue
        field_names: frozenset[str] = frozenset(
            statement.target.id
            for statement in node.body
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
        )
        if code == SftCode.TEST_TYPES_DESCRIPTION and "description" not in field_names:
            faults.append(ctx.fault(node))
        if code == SftCode.TEST_TYPES_EXPECTED_FIELD and not any(
            field_name.startswith("expected_") for field_name in field_names
        ):
            faults.append(ctx.fault(node))
    return faults


def _scenario_models_faults(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    faults: list[Fault] = []
    for node in module.body:
        if _is_docstring_statement(node) or isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if isinstance(node, ast.ClassDef) and _has_dataclass_decorator(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def _test_file_faults(*, module: ast.Module, ctx: RuleContext, code: SftCode) -> list[Fault]:
    local_test_types: _LocalTestTypes | None = None
    if code in {
        SftCode.LOCAL_TEST_TYPES_IMPORT,
        SftCode.TEST_CASE_ANNOTATION,
        SftCode.LOCAL_TEST_CASE_CONSTRUCTORS,
    } and _is_test_module(ctx.path):
        local_test_types = _local_test_types(
            path=ctx.path,
            repo_root=ctx.repo_root,
            inspect_dataclasses=code != SftCode.LOCAL_TEST_TYPES_IMPORT,
        )
    module_context: _TestModuleContext = _module_context(
        module=module, ctx=ctx, local_test_types=local_test_types
    )
    faults: list[Fault] = []
    if (
        code == SftCode.LOCAL_TEST_TYPES_FILE
        and _is_test_module(ctx.path)
        and not (ctx.path.parent / "_test_types.py").is_file()
    ):
        faults.append(ctx.fault(module))
    if (
        code == SftCode.TEST_FILE_NAME
        and _is_test_module(ctx.path)
        and not ctx.path.name.startswith("test_")
    ):
        faults.append(ctx.fault(module))
    faults.extend(_module_shape_faults(module=module, ctx=ctx, code=code))
    faults.extend(
        _local_import_faults(module=module, ctx=ctx, code=code, local_test_types=local_test_types)
    )
    for node in (*ctx.nodes(ast.FunctionDef), *ctx.nodes(ast.AsyncFunctionDef)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
            "test_"
        ):
            faults.extend(
                _test_function_faults(
                    function_node=node, ctx=ctx, code=code, module_context=module_context
                )
            )
    return faults


def _module_shape_faults(*, module: ast.Module, ctx: RuleContext, code: SftCode) -> list[Fault]:
    if not _is_test_module(ctx.path):
        return []
    faults: list[Fault] = []
    first_test_function_line: int | None = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith(
            "test_"
        ):
            if code == SftCode.NO_TOP_LEVEL_HELPERS:
                faults.append(ctx.fault(node))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
            "test_"
        ):
            if first_test_function_line is None:
                first_test_function_line = node.lineno
        if code == SftCode.NO_MODULE_TEST_CASE_LISTS and _is_test_case_list_assignment(node):
            faults.append(ctx.fault(node))
        if (
            code == SftCode.PRIVATE_CONSTANT_ORDER
            and first_test_function_line is not None
            and _is_private_assignment(node)
        ):
            faults.append(ctx.fault(node))
    return faults


def _local_import_faults(
    *,
    module: ast.Module,
    ctx: RuleContext,
    code: SftCode,
    local_test_types: _LocalTestTypes | None,
) -> list[Fault]:
    if code != SftCode.LOCAL_TEST_TYPES_IMPORT or local_test_types is None:
        return []
    faults: list[Fault] = []
    expected_module: str = local_test_types.module_name
    for node in module.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.endswith("._test_types")
        ):
            if node.module != expected_module:
                faults.append(ctx.fault(node))
    return faults


def _test_function_faults(
    *,
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ctx: RuleContext,
    code: SftCode,
    module_context: _TestModuleContext,
) -> list[Fault]:
    faults: list[Fault] = []
    if code == SftCode.TEST_FUNCTION_NAME and not _test_name_pattern.match(function_node.name):
        faults.append(ctx.fault(function_node))
    parametrize: ast.Call | None = _parametrize_decorator(function_node)
    if parametrize is None:
        if code == SftCode.DATACLASS_PARAMETRIZE:
            faults.append(ctx.fault(function_node))
        return faults
    test_case_arg: ast.arg | None = next(
        (argument for argument in function_node.args.args if argument.arg == "test_case"), None
    )
    if code == SftCode.ACCEPTS_TEST_CASE and test_case_arg is None:
        faults.append(ctx.fault(function_node))
    if code == SftCode.TEST_CASE_ANNOTATION and (
        test_case_arg is None
        or not isinstance(test_case_arg.annotation, ast.Name)
        or test_case_arg.annotation.id not in module_context.test_case_annotation_names
    ):
        faults.append(ctx.fault(function_node))
    faults.extend(
        _parametrize_faults(
            function_node=function_node,
            ctx=ctx,
            code=code,
            decorator=parametrize,
            module_context=module_context,
        )
    )
    if code == SftCode.NO_IF_IN_TESTS:
        faults.extend(
            ctx.fault(node) for node in ast.walk(function_node) if isinstance(node, ast.If)
        )
    if code == SftCode.EXPECTED_FIELD_ASSERTION and not _references_expected_field(function_node):
        faults.append(ctx.fault(function_node))
    return faults


def _parametrize_faults(
    *,
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ctx: RuleContext,
    code: SftCode,
    decorator: ast.Call,
    module_context: _TestModuleContext,
) -> list[Fault]:
    if len(decorator.args) < 2:
        return [ctx.fault(function_node)] if code == SftCode.PARAMETRIZE_ARGUMENTS else []
    parameter_name: str | None = _extract_string(decorator.args[0])
    faults: list[Fault] = []
    if code == SftCode.PARAMETRIZE_TEST_CASE and parameter_name != "test_case":
        faults.append(ctx.fault(function_node))
    ids_expression: ast.expr | None = next(
        (keyword.value for keyword in decorator.keywords if keyword.arg == "ids"), None
    )
    if code == SftCode.PARAMETRIZE_IDS and ids_expression is None:
        faults.append(ctx.fault(function_node))
    values_expression: ast.expr = decorator.args[1]
    if isinstance(values_expression, ast.Name):
        return faults + (
            [ctx.fault(function_node)] if code == SftCode.INLINE_PARAMETRIZE_VALUES else []
        )
    if isinstance(values_expression, ast.ListComp):
        if code == SftCode.LOCAL_TEST_CASE_CONSTRUCTORS and not _is_local_constructor(
            node=values_expression.elt, context=module_context
        ):
            faults.append(ctx.fault(values_expression.elt))
        if code == SftCode.DESCRIPTION_LAMBDA_IDS and not _is_description_lambda_ids(
            ids_expression
        ):
            faults.append(ctx.fault(function_node))
        return faults
    if not isinstance(values_expression, ast.List | ast.Tuple):
        return faults + (
            [ctx.fault(function_node)] if code == SftCode.INLINE_PARAMETRIZE_SEQUENCE else []
        )
    if code == SftCode.NONEMPTY_PARAMETRIZE_VALUES and not values_expression.elts:
        faults.append(ctx.fault(function_node))
    for element in values_expression.elts:
        if code == SftCode.NO_DICT_TEST_CASES and isinstance(element, ast.Dict):
            faults.append(ctx.fault(element))
        elif code == SftCode.LOCAL_TEST_CASE_CONSTRUCTORS and not _is_local_constructor(
            node=element, context=module_context
        ):
            faults.append(ctx.fault(element))
    if code == SftCode.DESCRIPTION_LAMBDA_IDS and not _is_description_lambda_ids(ids_expression):
        faults.append(ctx.fault(function_node))
    return faults


def _local_test_types(*, path: Path, repo_root: Path, inspect_dataclasses: bool) -> _LocalTestTypes:
    test_types_path: Path = path.parent / "_test_types.py"
    dataclass_names: frozenset[str] = frozenset()
    if inspect_dataclasses and test_types_path.is_file():
        file_stat: os.stat_result = test_types_path.stat()
        source: str = _test_types_source(
            path=test_types_path,
            modified_ns=file_stat.st_mtime_ns,
            changed_ns=file_stat.st_ctime_ns,
            size=file_stat.st_size,
        )
        dataclass_names = _dataclass_names(source)
    return _LocalTestTypes(
        module_name=_module_name_for_file(path=test_types_path, repo_root=repo_root),
        dataclass_names=dataclass_names,
    )


@lru_cache(maxsize=512)
def _test_types_source(*, path: Path, modified_ns: int, changed_ns: int, size: int) -> str:
    del modified_ns, changed_ns, size
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=512)
def _dataclass_names(source: str) -> frozenset[str]:
    try:
        module: ast.Module = ast.parse(source)
    except SyntaxError:
        return frozenset()
    return frozenset(
        node.name
        for node in module.body
        if isinstance(node, ast.ClassDef) and _has_dataclass_decorator(node)
    )


def _module_context(
    *, module: ast.Module, ctx: RuleContext, local_test_types: _LocalTestTypes | None
) -> _TestModuleContext:
    if local_test_types is None:
        return _TestModuleContext(
            imported_local_test_case_types=frozenset(),
            test_case_annotation_names=frozenset(),
        )
    imported: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module == local_test_types.module_name:
            for imported_name in node.names:
                if imported_name.name in local_test_types.dataclass_names:
                    imported.add(imported_name.asname or imported_name.name)
    del ctx
    return _TestModuleContext(
        imported_local_test_case_types=frozenset(imported),
        test_case_annotation_names=frozenset(imported),
    )


def _module_name_for_file(*, path: Path, repo_root: Path) -> str:
    return ".".join(path.relative_to(repo_root).with_suffix("").parts)


def _is_test_module(path: Path) -> bool:
    return path.name not in {
        "_test_helpers.py",
        "_test_types.py",
        "helpers.py",
        "conftest.py",
        "__init__.py",
    }


def _is_docstring_only_module(module: ast.Module) -> bool:
    return not module.body or (len(module.body) == 1 and _is_docstring_statement(module.body[0]))


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _has_dataclass_decorator(node: ast.ClassDef) -> bool:
    return any(
        _decorator_name(decorator).endswith("dataclass") for decorator in node.decorator_list
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


def _parametrize_decorator(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.Call | None:
    for decorator in function_node.decorator_list:
        if (
            isinstance(decorator, ast.Call)
            and _decorator_name(decorator.func) == "pytest.mark.parametrize"
        ):
            return decorator
    return None


def _extract_string(node: ast.expr) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


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


def _references_expected_field(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(function_node):
        if isinstance(node, ast.Attribute):
            chain: tuple[str, ...] | None = _attribute_chain(node)
            if (
                chain
                and len(chain) >= 2
                and chain[0] == "test_case"
                and chain[-1].startswith("expected_")
            ):
                return True
    return False


def _is_local_constructor(*, node: ast.expr, context: _TestModuleContext) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in context.imported_local_test_case_types
    )


def _is_description_lambda_ids(node: ast.expr | None) -> bool:
    if not isinstance(node, ast.Lambda) or len(node.args.args) != 1:
        return False
    if node.args.args[0].arg != "case":
        return False
    return _attribute_chain(node.body) == ("case", "description")


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
    return name == "TEST_CASES" or name.endswith("_TEST_CASES")


def _is_private_assignment(node: ast.stmt) -> bool:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id.startswith("_")
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id.startswith("_") for target in node.targets
        )
    return False


def _layout_codes() -> frozenset[SftCode]:
    return frozenset(
        {
            SftCode.TEST_LAYOUT,
            SftCode.TEST_SCOPE,
            SftCode.TEST_MIRRORED_ROOT,
            SftCode.SRC_MIRROR_DEPTH,
            SftCode.SRC_PACKAGE_EXISTS,
            SftCode.SRC_AREA_EXISTS,
            SftCode.SCRIPTS_MIRROR_DEPTH,
            SftCode.SCRIPTS_AREA_EXISTS,
        }
    )
