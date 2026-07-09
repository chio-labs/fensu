"""Rule check functions for the roles family."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext, Threshold
from strata.rules.roles.helpers.classification import (
    is_dataclass_class,
    is_exception_class,
    is_model_class,
    is_newtype_assignment,
    is_public_type_alias,
    is_type_checking_import_block,
    is_type_class,
    non_docstring_body,
)
from strata.rules.roles.types import RoleCode

_banned_generic_filenames: frozenset[str] = frozenset({"misc.py"})
_banned_generic_package_names: frozenset[str] = frozenset(
    {"base", "common", "lib", "misc", "shared", "util", "utils"}
)
_role_names: frozenset[str] = frozenset(
    {"helpers", "classes", "models", "types", "constants", "exceptions"}
)
_role_filenames: frozenset[str] = frozenset(
    {"models.py", "types.py", "constants.py", "exceptions.py", "helpers.py"}
)


def models_only_models(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in model-role modules."""

    if ctx.role_of() != "models":
        return []
    faults: list[Fault] = []
    for node in non_docstring_body(module):
        if isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if isinstance(node, ast.ClassDef) and is_model_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def types_only_types(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag runtime declarations in type-role modules."""

    if ctx.role_of() != "types":
        return []
    faults: list[Fault] = []
    allowed_nodes: tuple[type[ast.stmt], ...] = (
        ast.Import,
        ast.ImportFrom,
        ast.Assign,
        ast.AnnAssign,
        ast.TypeAlias,
    )
    for node in non_docstring_body(module):
        if isinstance(node, allowed_nodes) or is_type_checking_import_block(node):
            continue
        if isinstance(node, ast.ClassDef) and is_type_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def constants_only_constants(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in constant-role modules."""

    if ctx.role_of() != "constants":
        return []
    allowed_nodes: tuple[type[ast.stmt], ...] = (
        ast.Import,
        ast.ImportFrom,
        ast.Assign,
        ast.AnnAssign,
    )
    return [
        ctx.fault(node)
        for node in non_docstring_body(module)
        if not isinstance(node, allowed_nodes)
    ]


def exceptions_only_exceptions(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in exception-role modules."""

    if ctx.role_of() != "exceptions":
        return []
    faults: list[Fault] = []
    for node in non_docstring_body(module):
        if isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if isinstance(node, ast.ClassDef) and is_exception_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def model_declaration_outside_models(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag structured model declarations outside the models role."""

    if ctx.role_of() == "models":
        return []
    return [
        ctx.fault(node)
        for node in ast.walk(module)
        if isinstance(node, ast.ClassDef) and is_model_class(node)
    ]


def type_declaration_outside_types(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public type-layer declarations outside the types role."""

    if ctx.role_of() == "types":
        return []
    faults: list[Fault] = []
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef) and is_type_class(node):
            if node.name.startswith("_") and ctx.in_role("helpers"):
                continue
            faults.append(ctx.fault(node))
        elif isinstance(node, ast.stmt) and (
            is_public_type_alias(node) or is_newtype_assignment(node)
        ):
            faults.append(ctx.fault(node))
    return faults


def constant_outside_constants(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public uppercase module constants outside the constants role."""

    if ctx.role_of() == "constants":
        return []
    faults: list[Fault] = []
    for node in non_docstring_body(module):
        for target_name in _assignment_target_names(node):
            if not target_name.startswith("_") and target_name.isupper():
                faults.append(ctx.fault(node))
    return faults


def exception_declaration_outside_exceptions(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Flag custom exception declarations outside the exceptions role."""

    if ctx.role_of() == "exceptions":
        return []
    return [
        ctx.fault(node)
        for node in ast.walk(module)
        if isinstance(node, ast.ClassDef) and is_exception_class(node)
    ]


def banned_generic_filename(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag vague generic module filenames."""

    del module
    if ctx.path.name not in _banned_generic_filenames:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.BANNED_GENERIC_FILENAME,
            message="misc.py hides the module's purpose",
        )
    ]


def banned_generic_package_name(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag generic domain and subdomain package names."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    for index, package_name in enumerate(parts[:2]):
        if package_name not in _banned_generic_package_names:
            continue
        package_dir: Path = ctx.path.parents[len(parts) - index - 2]
        if not _is_package_name_anchor(path=ctx.path, package_dir=package_dir):
            return []
        return [
            _path_fault(
                ctx=ctx,
                code=RoleCode.BANNED_GENERIC_PACKAGE_NAME,
                message=(
                    f"{package_name}/ does not identify an owning domain; "
                    "name the business or technical capability"
                ),
            )
        ]
    return []


def helpers_module_name(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag helpers.py in favor of a helpers package."""

    del module
    if ctx.path.name != "helpers.py":
        return []
    return [Fault(code="SFR202", path=ctx.path, message="use a helpers/ package")]


def classes_module_name(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag classes.py in favor of a classes package."""

    del module
    if ctx.path.name != "classes.py":
        return []
    return [Fault(code="SFR203", path=ctx.path, message="use a classes/ package")]


def helpers_classes_file_private(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public plain classes in helpers modules."""

    if not ctx.in_role("helpers"):
        return []
    faults: list[Fault] = []
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        if is_model_class(node) or is_type_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def no_import_time_side_effects(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag standalone calls that execute while a runtime module is imported."""

    return [ctx.fault(node) for node in _import_time_bare_calls(node=module)]


def helpers_package_layout(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag mixed or oversized flat helpers package layouts."""

    del module
    package_dir: Path | None = _role_package_dir(path=ctx.path, package_name="helpers")
    if package_dir is None or not _is_package_layout_anchor(path=ctx.path, package_dir=package_dir):
        return []
    return _package_layout_faults(
        ctx=ctx,
        package_dir=package_dir,
        ignored_subfolders=frozenset(),
        threshold=Threshold.MAX_FLAT_HELPER_MODULES,
    )


def main_package_layout(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag mixed, oversized, or support-nested main package layouts."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    for index, part in enumerate(parts[:-1]):
        if (
            part == "main"
            and index + 1 < len(parts)
            and parts[index + 1]
            in {
                "helpers",
                "shared",
                "classes",
            }
        ):
            return [
                _path_fault(
                    ctx=ctx,
                    code=RoleCode.MAIN_PACKAGE_LAYOUT,
                    message="main packages must not contain support folders",
                )
            ]
    package_dir: Path | None = _role_package_dir(path=ctx.path, package_name="main")
    if package_dir is None or not _is_package_layout_anchor(path=ctx.path, package_dir=package_dir):
        return []
    return _package_layout_faults(
        ctx=ctx,
        package_dir=package_dir,
        ignored_subfolders=frozenset({"helpers", "shared", "classes"}),
        threshold=Threshold.MAX_FLAT_MAIN_MODULES,
    )


def nested_direct_modules(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag ad hoc direct modules in nested non-role packages."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) < 3 or "main" in parts[:-1]:
        return []
    if any(part in _role_names for part in parts[:-1]) or parts[-1] in {
        "__init__.py",
        *_role_filenames,
    }:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.NESTED_DIRECT_MODULES,
            message="nested packages must move support code under helpers/",
        )
    ]


def nested_direct_subpackages(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag arbitrary direct child packages below nested runtime packages."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) < 4 or "main" in parts[:-1]:
        return []
    allowed_children: frozenset[str] = frozenset(
        {"helpers", "shared", "classes", "models", "types", "constants", "exceptions", "main"}
    )
    package_parts: tuple[str, ...] = parts[:-1]
    for index in range(2, len(package_parts)):
        parent: str = package_parts[index - 1]
        child: str = package_parts[index]
        if parent in _role_names or child in allowed_children:
            continue
        return [
            _path_fault(
                ctx=ctx,
                code=RoleCode.NESTED_DIRECT_SUBPACKAGES,
                message="nested packages must use explicit role boundaries",
            )
        ]
    return []


def top_level_role_placement(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag role files and directories directly below top-level domains."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) < 2 or parts[0] == "shared":
        return []
    if len(parts) == 2 and parts[1] in {*_role_filenames, "classes.py"}:
        return [
            _path_fault(
                ctx=ctx,
                code=RoleCode.TOP_LEVEL_ROLE_PLACEMENT,
                message="top-level domains must not contain role files",
            )
        ]
    if len(parts) >= 3 and parts[1] in _role_names:
        return [
            _path_fault(
                ctx=ctx,
                code=RoleCode.TOP_LEVEL_ROLE_PLACEMENT,
                message="top-level domains must not contain role directories",
            )
        ]
    return []


def top_level_direct_modules(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag non-role modules directly below top-level domains."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) != 2 or parts[-1] in {"__init__.py", *_role_filenames}:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.TOP_LEVEL_DIRECT_MODULES,
            message="top-level domains must contain subpackages",
        )
    ]


def entry_module_shape(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag entry modules that are not focused single-entry surfaces."""

    if not ctx.is_entry_module():
        return []
    body: tuple[ast.stmt, ...] = non_docstring_body(module)
    public_functions: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...] = tuple(
        node
        for node in body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    )
    private_functions: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...] = tuple(
        node
        for node in body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("_")
    )
    faults: list[Fault] = []
    if len(public_functions) != 1:
        faults.append(
            _path_fault(
                ctx=ctx,
                code=RoleCode.ENTRY_MODULE_SHAPE,
                message="entry modules need one public function",
            )
        )
    if len(private_functions) > 2:
        faults.append(ctx.fault(private_functions[2]))
    for node in body:
        if isinstance(node, ast.Import | ast.ImportFrom | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        faults.append(ctx.fault(node))
    return faults


def init_module_empty(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag non-root package initializers containing runtime statements."""

    if ctx.path.name != "__init__.py" or len(ctx.relative_parts()) == 1:
        return []
    if not module.body or (len(module.body) == 1 and _is_docstring_statement(module.body[0])):
        return []
    return [
        _path_fault(
            ctx=ctx, code=RoleCode.INIT_MODULE_EMPTY, message="nested __init__.py must be empty"
        )
    ]


def no_reexport_shim(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag internal modules that only re-export imports."""

    if ctx.path.name == "__init__.py" or ctx.role_of() == "exceptions":
        return []
    if not _is_pure_reexport_module(module):
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.NO_REEXPORT_SHIM,
            message="internal modules must not be re-export shims",
        )
    ]


def no_internal_helper_exports(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag __all__ declarations inside helpers packages."""

    if not ctx.in_role("helpers"):
        return []
    return [ctx.fault(node) for node in module.body if _is_all_assignment(node)]


def main_entry_name_collision(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag a main entry module sharing its name with a sibling package."""

    del module
    if not ctx.is_entry_module() or not ctx.path.with_suffix("").is_dir():
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.MAIN_ENTRY_NAME_COLLISION,
            message="main entry name collides with package",
        )
    ]


def public_surface_shape(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Restrict the root package surface to imports and one __all__ declaration."""

    if ctx.path.name != "__init__.py" or len(ctx.relative_parts()) != 1:
        return []
    faults: list[Fault] = []
    saw_all: bool = False
    for node in module.body:
        if _is_docstring_statement(node) or isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if _is_all_assignment(node):
            if saw_all:
                faults.append(ctx.fault(node, message="public surface may define __all__ once"))
            saw_all = True
            continue
        faults.append(ctx.fault(node))
    return faults


def classes_one_class_per_module(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag classes modules that do not define exactly one top-level class."""

    if not ctx.in_role("classes") or ctx.path.name == "__init__.py":
        return []
    class_nodes: tuple[ast.ClassDef, ...] = tuple(
        node for node in module.body if isinstance(node, ast.ClassDef)
    )
    if len(class_nodes) == 1:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.CLASSES_ONE_CLASS_PER_MODULE,
            message="classes modules must define one class",
        )
    ]


def helpers_package_shape(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag orchestration and deep nesting below helpers packages."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    if "helpers" not in parts[:-1]:
        return []
    helpers_index: int = parts.index("helpers")
    depth: int = len(parts) - helpers_index - 1
    if depth == 1 and ctx.path.name != "main.py":
        return []
    if depth == 2 and ctx.path.name != "main.py":
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.HELPERS_PACKAGE_SHAPE,
            message="helpers packages must stay shallow",
        )
    ]


def private_definition_ordering(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag private dataclasses and constants after top-level functions."""

    faults: list[Fault] = []
    saw_function: bool = False
    for node in module.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            saw_function = True
            continue
        if not saw_function:
            continue
        if (
            isinstance(node, ast.ClassDef)
            and node.name.startswith("_")
            and is_dataclass_class(node)
        ):
            faults.append(ctx.fault(node))
        elif any(name.startswith("_") for name in _assignment_target_names(node)):
            faults.append(ctx.fault(node))
    return faults


def source_file_line_count(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag runtime source files exceeding the configured line limit."""

    del module
    line_count: int = len(ctx.source.splitlines())
    if line_count <= ctx.threshold(Threshold.MAX_FILE_LINES):
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.SOURCE_FILE_LINE_COUNT,
            message=f"source file has {line_count} lines",
        )
    ]


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_all_assignment(node: ast.stmt) -> bool:
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        )
    return (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "__all__"
    )


def _is_pure_reexport_module(module: ast.Module) -> bool:
    saw_import: bool = False
    saw_all: bool = False
    for node in module.body:
        if _is_docstring_statement(node):
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        if isinstance(node, ast.Import | ast.ImportFrom):
            saw_import = True
            continue
        if _is_all_assignment(node):
            saw_all = True
            continue
        return False
    return saw_import and saw_all


def _role_package_dir(*, path: Path, package_name: str) -> Path | None:
    if path.parent.name == package_name:
        return path.parent
    if path.parent.parent.name == package_name:
        return path.parent.parent
    return None


def _is_package_layout_anchor(*, path: Path, package_dir: Path) -> bool:
    init_path: Path = package_dir / "__init__.py"
    if init_path.exists():
        return path == init_path
    direct_modules: tuple[Path, ...] = tuple(
        sorted(child for child in package_dir.glob("*.py") if child.name != "__init__.py")
    )
    return bool(direct_modules) and path == direct_modules[0]


def _is_package_name_anchor(*, path: Path, package_dir: Path) -> bool:
    init_path: Path = package_dir / "__init__.py"
    if init_path.exists():
        return path == init_path
    modules: tuple[Path, ...] = tuple(sorted(package_dir.rglob("*.py")))
    return bool(modules) and path == modules[0]


def _import_time_bare_calls(*, node: ast.AST) -> tuple[ast.Expr, ...]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
        return ()
    if isinstance(node, ast.If) and _is_nonexecuting_import_guard(node.test):
        return tuple(
            call for statement in node.orelse for call in _import_time_bare_calls(node=statement)
        )
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return (node,)
    return tuple(
        call for child in ast.iter_child_nodes(node) for call in _import_time_bare_calls(node=child)
    )


def _is_nonexecuting_import_guard(node: ast.expr) -> bool:
    if isinstance(node, ast.Name) and node.id == "TYPE_CHECKING":
        return True
    if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    if not isinstance(node.left, ast.Name) or node.left.id != "__name__":
        return False
    comparator: ast.expr = node.comparators[0]
    return (
        isinstance(node.ops[0], ast.Eq)
        and isinstance(comparator, ast.Constant)
        and comparator.value == "__main__"
    )


def _package_layout_faults(
    *,
    ctx: RuleContext,
    package_dir: Path,
    ignored_subfolders: frozenset[str],
    threshold: Threshold,
) -> list[Fault]:
    direct_modules: tuple[Path, ...] = tuple(
        child
        for child in package_dir.glob("*.py")
        if child.name != "__init__.py" and child.is_file()
    )
    concern_subfolders: tuple[Path, ...] = tuple(
        child
        for child in package_dir.iterdir()
        if child.is_dir() and child.name != "__pycache__" and child.name not in ignored_subfolders
    )
    faults: list[Fault] = []
    code: RoleCode = (
        RoleCode.HELPERS_PACKAGE_LAYOUT
        if threshold == Threshold.MAX_FLAT_HELPER_MODULES
        else RoleCode.MAIN_PACKAGE_LAYOUT
    )
    if direct_modules and concern_subfolders:
        faults.append(
            _path_fault(
                ctx=ctx,
                code=code,
                message="role package mixes flat modules and subfolders",
            )
        )
    if len(direct_modules) > ctx.threshold(threshold):
        faults.append(
            _path_fault(ctx=ctx, code=code, message="role package has too many flat modules")
        )
    return faults


def _path_fault(*, ctx: RuleContext, code: RoleCode, message: str) -> Fault:
    return Fault(code=code, path=ctx.path, message=message)


def _assignment_target_names(node: ast.stmt) -> tuple[str, ...]:
    if isinstance(node, ast.Assign):
        return tuple(target.id for target in node.targets if isinstance(target, ast.Name))
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return (node.target.id,)
    return ()
