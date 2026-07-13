"""Rule check functions for the roles family."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.analysis.models import ModuleDeclarationFacts, ModuleStatementFact
from strata.discovery.constants import (
    HELPERS_DIRECTORY_NAME,
    INIT_MODULE_FILE_NAME,
    LEGACY_HELPERS_DIRECTORY_NAME,
    PYTHON_FILE_SUFFIX,
    ROLE_DIRECTORY_TO_NAME,
)
from strata.discovery.types import RoleName, ScopeName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext, Threshold
from strata.rules.roles.types import RoleCode

_banned_generic_filenames: frozenset[str] = frozenset({"misc.py"})
_banned_generic_package_names: frozenset[str] = frozenset(
    {"base", "common", "helpers", "lib", "misc", "shared", "util", "utils"}
)
_role_names: frozenset[str] = frozenset(
    {
        RoleName.MAIN,
        HELPERS_DIRECTORY_NAME,
        RoleName.CLASSES,
        RoleName.MODELS,
        RoleName.TYPES,
        RoleName.CONSTANTS,
        RoleName.EXCEPTIONS,
    }
)
_role_filenames: frozenset[str] = frozenset(
    {
        "main.py",
        "helpers.py",
        "classes.py",
        "models.py",
        "types.py",
        "constants.py",
        "exceptions.py",
    }
)
_tooling_private_function_names: frozenset[str] = frozenset({"_build_parser", "_parse_args"})
_tooling_role_names: frozenset[str] = frozenset(
    {RoleName.MAIN, HELPERS_DIRECTORY_NAME, RoleName.CLASSES, RoleName.RULES}
)
_classes_module_file_name: str = "classes.py"
_helpers_module_file_name: str = "helpers.py"
_main_module_file_name: str = "main.py"
_python_cache_directory_name: str = "__pycache__"
_minimum_nested_module_parts: int = 3
_minimum_nested_subpackage_parts: int = 4
_top_level_role_parts: int = 2
_maximum_entry_private_functions: int = 2


def models_only_models(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in model-role modules."""

    if ctx.role_of() != RoleName.MODELS:
        return []
    del module
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement and not fact.model_class
    ]


def types_only_types(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag runtime declarations in type-role modules."""

    if ctx.role_of() != RoleName.TYPES:
        return []
    del module
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement
        and not fact.assignment_statement
        and not fact.explicit_type_alias
        and not fact.type_checking_import_block
        and not fact.type_class
    ]


def constants_only_constants(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in constant-role modules."""

    if ctx.role_of() != RoleName.CONSTANTS:
        return []
    del module
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement and not fact.assignment_statement
    ]


def exceptions_only_exceptions(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in exception-role modules."""

    if ctx.role_of() != RoleName.EXCEPTIONS:
        return []
    del module
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement and not fact.exception_class
    ]


def model_declaration_outside_models(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag structured model declarations outside the models role."""

    if ctx.role_of() == RoleName.MODELS:
        return []
    del module
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.module_declarations().model_locations
    ]


def type_declaration_outside_types(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public type-layer declarations outside the types role."""

    if ctx.role_of() == RoleName.TYPES:
        return []
    del module
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().type_declarations
        if not fact.private or not ctx.in_role(RoleName.HELPERS)
    ]


def constant_outside_constants(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public uppercase module constants outside the constants role."""

    if ctx.role_of() == RoleName.CONSTANTS:
        return []
    del module
    faults: list[Fault] = []
    for fact in ctx.facts.module_declarations().statements:
        for target_name in fact.assignment_target_names:
            if not target_name.startswith("_") and target_name.isupper():
                faults.append(ctx.fault_at(location=fact.location))
    return faults


def exception_declaration_outside_exceptions(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Flag custom exception declarations outside the exceptions role."""

    if ctx.role_of() == RoleName.EXCEPTIONS:
        return []
    del module
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.module_declarations().exception_locations
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
    """Flag generic runtime package directory names at any depth."""

    del module
    if ctx.scope() is ScopeName.TOOLING:
        return []
    parts: tuple[str, ...] = ctx.relative_parts()
    faults: list[Fault] = []
    for index, package_name in enumerate(parts[:-1]):
        if package_name not in _banned_generic_package_names:
            continue
        package_dir: Path = ctx.path.parents[len(parts) - index - 2]
        if not _is_package_name_anchor(ctx=ctx, path=ctx.path, package_dir=package_dir):
            continue
        faults.append(
            _path_fault(
                ctx=ctx,
                code=RoleCode.BANNED_GENERIC_PACKAGE_NAME,
                message=(
                    f"{package_name}/ does not identify an owner; "
                    "name the business or technical capability"
                ),
            )
        )
    return faults


def helpers_module_name(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag helpers.py in favor of a helpers package."""

    del module
    if ctx.path.name != _helpers_module_file_name:
        return []
    return [ctx.path_fault(message="use an _helpers/ package")]


def classes_module_name(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag classes.py in favor of a classes package."""

    del module
    if ctx.path.name != _classes_module_file_name:
        return []
    return [ctx.path_fault(message="use a classes/ package")]


def helpers_classes_file_private(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public plain classes in helpers modules."""

    if not ctx.in_role(RoleName.HELPERS):
        return []
    del module
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if fact.class_name is not None
        and not fact.class_name.startswith("_")
        and not fact.model_class
        and not fact.type_class
    ]


def helpers_package_layout(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag helpers containers that violate the shared role-container model."""

    del module
    package_dir: Path | None = _role_package_dir(ctx=ctx, role=RoleName.HELPERS)
    if package_dir is None:
        return []
    return _package_layout_faults(
        ctx=ctx,
        package_dir=package_dir,
        role=RoleName.HELPERS,
        threshold=Threshold.MAX_HELPERS_CONTAINER_MODULES,
    )


def main_package_layout(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag main containers that violate the shared role-container model."""

    del module
    package_dir: Path | None = _role_package_dir(ctx=ctx, role=RoleName.MAIN)
    if package_dir is None:
        return []
    return _package_layout_faults(
        ctx=ctx,
        package_dir=package_dir,
        role=RoleName.MAIN,
        threshold=Threshold.MAX_MAIN_CONTAINER_MODULES,
    )


def nested_direct_modules(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag ad hoc direct modules in nested non-role packages."""

    del module
    if ctx.scope() is ScopeName.TOOLING:
        return []
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) < _minimum_nested_module_parts or RoleName.MAIN in parts[:-1]:
        return []
    if any(part in _role_names for part in parts[:-1]) or parts[-1] in {
        INIT_MODULE_FILE_NAME,
        *_role_filenames,
    }:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.NESTED_DIRECT_MODULES,
            message="nested packages must move support code under _helpers/",
        )
    ]


def nested_direct_subpackages(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag arbitrary direct child packages below nested runtime packages."""

    del module
    if ctx.scope() is ScopeName.TOOLING:
        return []
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) < _minimum_nested_subpackage_parts or RoleName.MAIN in parts[:-1]:
        return []
    allowed_children: frozenset[str] = frozenset(
        {
            HELPERS_DIRECTORY_NAME,
            RoleName.CLASSES,
            RoleName.MODELS,
            RoleName.TYPES,
            RoleName.CONSTANTS,
            RoleName.EXCEPTIONS,
            RoleName.MAIN,
        }
    )
    package_parts: tuple[str, ...] = parts[:-1]
    if any(part in {HELPERS_DIRECTORY_NAME, RoleName.MAIN} for part in package_parts):
        return []
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


def top_level_domain_shape(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag top-level domains that mix direct roles with named subdomains."""

    del module
    if ctx.scope() is ScopeName.TOOLING:
        return []
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) < _top_level_role_parts:
        return []
    domain_dir: Path = ctx.path.parents[len(parts) - _top_level_role_parts]
    entries: tuple[Path, ...] = ctx.project.directory_entries(
        requester=ctx.path,
        path=domain_dir,
    )
    direct_role_content: tuple[Path, ...] = tuple(
        entry
        for entry in entries
        if entry.name in _role_names
        or (entry.suffix == PYTHON_FILE_SUFFIX and entry.name in _role_filenames)
    )
    named_subdomains: tuple[Path, ...] = tuple(
        entry
        for entry in entries
        if entry.name not in _role_names
        and entry.name != _python_cache_directory_name
        and ctx.project.is_dir(requester=ctx.path, path=entry)
        and ctx.project.glob(
            requester=ctx.path,
            path=entry,
            pattern="*.py",
            recursive=True,
        )
    )
    if not direct_role_content or not named_subdomains:
        return []
    init_path: Path = domain_dir / INIT_MODULE_FILE_NAME
    if ctx.project.is_file(requester=ctx.path, path=init_path):
        anchor: Path = init_path
    else:
        python_files: tuple[Path, ...] = tuple(
            sorted(
                ctx.project.glob(
                    requester=ctx.path,
                    path=domain_dir,
                    pattern="*.py",
                    recursive=True,
                )
            )
        )
        if not python_files:
            return []
        anchor = python_files[0]
    if ctx.path != anchor:
        return []
    return [ctx.path_fault(message="top-level domain mixes direct roles and named subdomains")]


def top_level_direct_modules(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag non-role modules directly below top-level domains."""

    del module
    if ctx.scope() is ScopeName.TOOLING:
        return []
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) != _top_level_role_parts or parts[-1] in {
        INIT_MODULE_FILE_NAME,
        *_role_filenames,
    }:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.TOP_LEVEL_DIRECT_MODULES,
            message="top-level domains must not contain ad hoc direct modules",
        )
    ]


def entry_module_shape(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag entry modules that are not focused single-entry surfaces."""

    if not ctx.is_entry_module():
        return []
    del module
    statements: tuple[ModuleStatementFact, ...] = ctx.facts.module_declarations().statements
    public_functions: tuple[ModuleStatementFact, ...] = tuple(
        fact for fact in statements if fact.function_name and not fact.function_name.startswith("_")
    )
    private_functions: tuple[ModuleStatementFact, ...] = tuple(
        fact for fact in statements if fact.function_name and fact.function_name.startswith("_")
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
    if len(private_functions) > _maximum_entry_private_functions:
        faults.append(
            ctx.fault_at(
                location=private_functions[2].location,
                message="main/ entry modules may define at most two private glue functions",
            )
        )
    for fact in statements:
        if fact.import_statement or fact.function_name is not None:
            continue
        faults.append(
            ctx.fault_at(
                location=fact.location,
                message="main/ entry modules may contain only imports and top-level functions",
            )
        )
    return faults


def init_module_empty(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag non-root package initializers containing runtime statements."""

    if ctx.path.name != INIT_MODULE_FILE_NAME or len(ctx.relative_parts()) == 1:
        return []
    del module
    if ctx.facts.module_declarations().empty_or_docstring_only:
        return []
    return [
        _path_fault(
            ctx=ctx, code=RoleCode.INIT_MODULE_EMPTY, message="nested __init__.py must be empty"
        )
    ]


def no_reexport_shim(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag internal modules that only re-export imports."""

    if ctx.path.name == INIT_MODULE_FILE_NAME or ctx.role_of() == RoleName.EXCEPTIONS:
        return []
    del module
    if not ctx.facts.module_declarations().pure_reexport:
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

    if not ctx.in_role(RoleName.HELPERS):
        return []
    del module
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.module_declarations().all_assignment_locations
    ]


def main_entry_name_collision(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag a main entry module sharing its name with a sibling package."""

    del module
    if not ctx.is_entry_module() or not ctx.project.is_dir(
        requester=ctx.path,
        path=ctx.path.with_suffix(""),
    ):
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

    if ctx.path.name != INIT_MODULE_FILE_NAME or len(ctx.relative_parts()) != 1:
        return []
    del module
    faults: list[Fault] = []
    saw_all: bool = False
    for fact in ctx.facts.module_declarations().statements:
        if fact.docstring_statement or fact.import_statement:
            continue
        if fact.all_assignment:
            if saw_all:
                faults.append(
                    ctx.fault_at(
                        location=fact.location,
                        message="public surface may define __all__ once",
                    )
                )
            saw_all = True
            continue
        faults.append(ctx.fault_at(location=fact.location))
    return faults


def classes_one_class_per_module(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag classes modules that do not define exactly one top-level class."""

    if not ctx.in_role(RoleName.CLASSES) or ctx.path.name == INIT_MODULE_FILE_NAME:
        return []
    del module
    if ctx.facts.module_declarations().top_level_class_count == 1:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.CLASSES_ONE_CLASS_PER_MODULE,
            message="classes modules must define one class",
        )
    ]


def helpers_package_shape(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag orchestration entrypoints below helpers packages."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    if HELPERS_DIRECTORY_NAME not in parts[:-1]:
        return []
    if ctx.path.name != _main_module_file_name:
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.HELPERS_PACKAGE_SHAPE,
            message="_helpers/ packages must not contain main.py orchestration",
        )
    ]


def private_definition_ordering(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag private dataclasses and constants after top-level functions."""

    faults: list[Fault] = []
    saw_function: bool = False
    del module
    for fact in ctx.facts.module_declarations().statements:
        if fact.function_name is not None:
            saw_function = True
            continue
        if not saw_function:
            continue
        if fact.class_name is not None and fact.class_name.startswith("_") and fact.dataclass_class:
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message="private dataclasses must appear before top-level functions",
                )
            )
        elif any(name.startswith("_") for name in fact.assignment_target_names):
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message="private constants must appear before top-level functions",
                )
            )
    return faults


def source_file_line_count(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag runtime source files exceeding the configured line limit."""

    del module
    line_count: int = len(ctx.source.splitlines())
    if line_count <= ctx.threshold(name=Threshold.MAX_FILE_LINES):
        return []
    return [
        _path_fault(
            ctx=ctx,
            code=RoleCode.SOURCE_FILE_LINE_COUNT,
            message=f"source file has {line_count} lines",
        )
    ]


def tooling_entrypoint_shape(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Keep direct scripts as one-public-function command adapters."""

    if not _is_direct_tooling_entrypoint(ctx):
        return []
    del module
    statements: tuple[ModuleStatementFact, ...] = ctx.facts.module_declarations().statements
    public_functions: tuple[ModuleStatementFact, ...] = tuple(
        fact for fact in statements if fact.function_name and not fact.function_name.startswith("_")
    )
    faults: list[Fault] = []
    main_functions: tuple[ModuleStatementFact, ...] = tuple(
        fact for fact in public_functions if fact.function_name == RoleName.MAIN
    )
    if not public_functions or len(main_functions) > 1:
        faults.append(
            ctx.path_fault(message="direct scripts must define exactly one public main() function")
        )
    for fact in statements:
        if fact.import_statement:
            continue
        if fact.function_name is not None:
            if (
                fact.function_name == RoleName.MAIN
                or fact.function_name in _tooling_private_function_names
            ):
                continue
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message=(
                        "direct scripts may define only main(), _parse_args(), and _build_parser()"
                    ),
                )
            )
            continue
        if fact.nonexecuting_import_guard:
            continue
        faults.append(
            ctx.fault_at(
                location=fact.location,
                message="direct scripts may contain only imports, command functions, and guards",
            )
        )
    return faults


def tooling_entrypoint_delegation(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Require direct scripts to call an imported main/ entry function."""

    if not _is_direct_tooling_entrypoint(ctx):
        return []
    del module
    facts: ModuleDeclarationFacts = ctx.facts.module_declarations()
    main_present: bool = any(fact.function_name == RoleName.MAIN for fact in facts.statements)
    if not main_present:
        return [
            ctx.path_fault(
                message="direct scripts must import and call an entry function from a main/ module"
            )
        ]
    imported_entries: frozenset[str] = facts.imported_main_entry_names
    delegates: bool = any(call.name in imported_entries for call in facts.main_calls)
    faults: list[Fault] = []
    if not delegates:
        faults.append(
            ctx.path_fault(
                message="direct scripts must import and call an entry function from a main/ module"
            )
        )
    allowed_calls: frozenset[str] = frozenset({"_parse_args", *imported_entries})
    for call in facts.main_calls:
        if call.name in allowed_calls:
            continue
        faults.append(
            ctx.fault_at(
                location=call.location,
                message=(
                    "direct script main() may call only _parse_args() and imported main/ entries"
                ),
            )
        )
    return faults


def tooling_entrypoint_line_count(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Keep direct script adapters below their configured line limit."""

    del module
    if not _is_direct_tooling_entrypoint(ctx):
        return []
    line_count: int = len(ctx.source.splitlines())
    limit: int = ctx.threshold(name=Threshold.MAX_SCRIPT_ENTRYPOINT_LINES)
    if line_count <= limit:
        return []
    return [ctx.path_fault(message=f"direct script has {line_count} lines (limit: {limit})")]


def rules_role_content(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Allow only decorated rule declarations in tooling rules/ modules."""

    if (
        ctx.scope() is not ScopeName.TOOLING
        or not ctx.in_role(RoleName.RULES)
        or ctx.path.name == INIT_MODULE_FILE_NAME
    ):
        return []
    del module
    faults: list[Fault] = []
    for fact in ctx.facts.module_declarations().statements:
        if fact.import_statement or fact.type_checking_import_block:
            continue
        if fact.rule_decorated_function:
            continue
        faults.append(
            ctx.fault_at(
                location=fact.location,
                message="rules/ modules may contain only imports and @rule functions",
            )
        )
    return faults


def tooling_package_layout(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Require tooling implementation packages to use direct role boundaries."""

    del module
    if ctx.scope() is not ScopeName.TOOLING:
        return []
    parts: tuple[str, ...] = ctx.relative_parts()
    if len(parts) < _top_level_role_parts:
        return []
    if len(parts) == _top_level_role_parts:
        if parts[-1] == INIT_MODULE_FILE_NAME or parts[-1] in _role_filenames:
            return []
        return [
            ctx.path_fault(message="tool packages may contain only role files and role directories")
        ]
    role_name: str = parts[1]
    if role_name in _tooling_role_names:
        return []
    package_dir: Path = ctx.path.parents[len(parts) - 3]
    if not _is_package_name_anchor(ctx=ctx, path=ctx.path, package_dir=package_dir):
        return []
    return [ctx.path_fault(message=f"tool package child '{role_name}/' is not an approved role")]


def _role_package_dir(*, ctx: RuleContext, role: RoleName) -> Path | None:
    parts: tuple[str, ...] = ctx.relative_parts()
    for index, part in enumerate(parts[:-1]):
        directory_role: RoleName | None = ROLE_DIRECTORY_TO_NAME.get(part)
        if directory_role is not None:
            if directory_role != role:
                return None
            return ctx.scope_root().joinpath(*parts[: index + 1])
    return None


def _is_direct_tooling_entrypoint(ctx: RuleContext) -> bool:
    parts: tuple[str, ...] = ctx.relative_parts()
    return (
        ctx.scope() is ScopeName.TOOLING
        and len(parts) == 1
        and ctx.path.suffix == PYTHON_FILE_SUFFIX
        and ctx.path.name != INIT_MODULE_FILE_NAME
    )


def _is_package_name_anchor(*, ctx: RuleContext, path: Path, package_dir: Path) -> bool:
    init_path: Path = package_dir / "__init__.py"
    if ctx.project.exists(requester=ctx.path, path=init_path):
        return path == init_path
    modules: tuple[Path, ...] = tuple(
        sorted(
            ctx.project.glob(
                requester=ctx.path,
                path=package_dir,
                pattern="*.py",
                recursive=True,
            )
        )
    )
    return bool(modules) and path == modules[0]


def _package_layout_faults(
    *,
    ctx: RuleContext,
    package_dir: Path,
    role: RoleName,
    threshold: Threshold,
) -> list[Fault]:
    relative_parts: tuple[str, ...] = ctx.path.relative_to(package_dir).parts
    container: Path = package_dir if len(relative_parts) == 1 else ctx.path.parent
    direct_modules: tuple[Path, ...] | None = _anchored_direct_modules(ctx=ctx, container=container)
    if direct_modules is None:
        return []
    faults: list[Fault] = []
    code: RoleCode = (
        RoleCode.HELPERS_PACKAGE_LAYOUT
        if role is RoleName.HELPERS
        else RoleCode.MAIN_PACKAGE_LAYOUT
    )
    depth: int = len(container.relative_to(package_dir).parts)
    module_limit: int = ctx.threshold(name=threshold, path=ctx.path)
    if direct_modules and _has_python_bucket(ctx=ctx, container=container):
        faults.append(
            _path_fault(
                ctx=ctx,
                code=code,
                message=(
                    f"{_physical_role_name(role)}/ container mixes direct modules "
                    "and Python buckets"
                ),
            )
        )
    if len(direct_modules) > module_limit:
        faults.append(
            _path_fault(
                ctx=ctx,
                code=code,
                message=(
                    f"{_physical_role_name(role)}/ container has {len(direct_modules)} modules; "
                    f"effective limit is {module_limit}"
                ),
            )
        )
    if depth > 0:
        depth_limit: int = ctx.threshold(name=Threshold.MAX_ROLE_DEPTH, path=ctx.path)
        if depth > depth_limit:
            faults.append(
                _path_fault(
                    ctx=ctx,
                    code=code,
                    message=(
                        f"{_physical_role_name(role)}/ bucket depth is {depth}; "
                        f"effective limit is {depth_limit}"
                    ),
                )
            )
        delegated_bucket_names: list[str] = []
        ancestor: Path = container.parent
        while ancestor != package_dir:
            if ctx.project.python_anchor(requester=ctx.path, path=ancestor) != ctx.path:
                break
            if _is_forbidden_role_bucket_name(ancestor.name):
                delegated_bucket_names.append(ancestor.name)
            ancestor = ancestor.parent
        bucket_names: tuple[str, ...] = (
            *reversed(delegated_bucket_names),
            *((container.name,) if _is_forbidden_role_bucket_name(container.name) else ()),
        )
        for bucket_name in bucket_names:
            faults.append(
                _path_fault(
                    ctx=ctx,
                    code=code,
                    message=(
                        f"{_physical_role_name(role)}/ bucket '{bucket_name}/' "
                        "uses a runtime role name"
                    ),
                )
            )
    return faults


def _anchored_direct_modules(*, ctx: RuleContext, container: Path) -> tuple[Path, ...] | None:
    if ctx.path.parent != container:
        return None
    init_path: Path = container / INIT_MODULE_FILE_NAME
    if ctx.path.name != INIT_MODULE_FILE_NAME and ctx.project.exists(
        requester=ctx.path, path=init_path
    ):
        return None
    direct_modules: tuple[Path, ...] = tuple(
        sorted(
            path
            for path in ctx.project.glob(
                requester=ctx.path,
                path=container,
                pattern="*.py",
            )
            if path.name != INIT_MODULE_FILE_NAME
        )
    )
    if ctx.path.name == INIT_MODULE_FILE_NAME:
        return direct_modules
    return direct_modules if direct_modules and ctx.path == direct_modules[0] else None


def _has_python_bucket(*, ctx: RuleContext, container: Path) -> bool:
    return any(
        path.parent != container
        for path in ctx.project.glob(
            requester=ctx.path,
            path=container,
            pattern="*.py",
            recursive=True,
        )
    )


def _is_forbidden_role_bucket_name(name: str) -> bool:
    return name in _role_names or name == LEGACY_HELPERS_DIRECTORY_NAME


def _physical_role_name(role: RoleName) -> str:
    return HELPERS_DIRECTORY_NAME if role is RoleName.HELPERS else role


def _path_fault(*, ctx: RuleContext, code: RoleCode, message: str) -> Fault:
    del code
    return ctx.path_fault(message=message)


def _assignment_target_names(node: ast.stmt) -> tuple[str, ...]:
    if isinstance(node, ast.Assign):
        return tuple(target.id for target in node.targets if isinstance(target, ast.Name))
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return (node.target.id,)
    return ()
