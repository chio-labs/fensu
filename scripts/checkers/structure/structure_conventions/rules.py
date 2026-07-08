"""Rule implementations for structure convention checks."""

from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

from scripts.checkers.structure.structure_conventions.constants import (
    BANNED_GENERIC_FILENAMES,
    DEV_TOOLING_FILE_PREFIXES,
    DEV_TOOLING_SEGMENTS,
    MODEL_CLASS_BASE_NAMES,
    RAW_BUILTIN_RAISE_NAMES,
    TYPE_CLASS_BASE_NAMES,
)
from scripts.checkers.structure.structure_conventions.models import Violation

_RUNTIME_PREFIX: tuple[str, str] = ("src", "strata")
_RUNTIME_PACKAGE_NAME: str = "strata"
_RUNTIME_PREFIX_TEXT: str = "src/strata/"
_TOOLING_ROOT_NAME: str = "scripts"
_MAX_TOOLING_ENTRYPOINT_LINES: int = 80
_TOOLING_ENTRYPOINT_ALLOWED_FUNCTION_NAMES: frozenset[str] = frozenset({"main", "parse_args"})

_MAX_SOURCE_FILE_LINES: int = 2000
_MAX_HELPER_FLAT_MODULES: int = 10
_MAX_MAIN_FLAT_MODULES: int = 20
_MAX_MAIN_PUBLIC_FUNCTION_STATEMENTS: int = 40
_MAX_MAIN_PUBLIC_FUNCTION_DISTINCT_CALLS: int = 20
_MAX_MAIN_PUBLIC_FUNCTION_LOCALS: int = 20
_PARAMETER_MUTATION_METHODS: frozenset[str] = frozenset(
    {"add", "append", "clear", "extend", "insert", "pop", "remove", "setdefault", "update"}
)
_DISCARDED_CALL_VALIDATOR_PREFIXES: frozenset[str] = frozenset({"check_", "enforce_", "validate_"})
_DISCARDED_CALL_CALLBACK_PREFIXES: frozenset[str] = frozenset({"on_", "report_"})
_DISCARDED_CALL_DIAGNOSTIC_PREFIXES: frozenset[str] = frozenset({"log"})
_DISCARDED_CALL_WRITER_PREFIXES: frozenset[str] = frozenset({"write_"})
_DISCARDED_CALL_ALLOWED_NAMES: frozenset[str] = frozenset({"print"})
_PARAMETER_MUTATION_EXEMPT_PARAMETERS: frozenset[str] = frozenset({"cls", "self"})
_PARAMETER_MUTATION_ALLOW_COMMENT: str = "# sc: allow-param-mutation"
_MAIN_PHASE_REMEDIATION_MESSAGE: str = (
    "main/ public functions are orchestrators: they should read as an ordered list of "
    "named phases. Extract cohesive stages into helpers/ functions that each accept "
    "explicit inputs and RETURN a named result model (no mutable threading), then call "
    "them in sequence. Do not create '_part_one'-style splits; name each phase after "
    "the result it produces (e.g. 'resolve_planner_scopes', 'detect_staleness')."
)
_MAIN_SUPPORT_FOLDER_NAMES: frozenset[str] = frozenset({"classes", "helpers", "shared"})
_RUNTIME_ROLE_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {"helpers", "classes", "models", "types", "constants", "exceptions"}
)
_SC056_COMMENT_ALLOWED_PREFIXES: tuple[str, ...] = (
    "#!",
    "# -*-",
    "# coding:",
    "# noqa",
    "# type: ignore",
    "# pyright:",
    "# pylint:",
    "# pragma:",
    _PARAMETER_MUTATION_ALLOW_COMMENT,
)
_DOCSTRING_BEARING_NODE_TYPES: tuple[type[ast.AST], ...] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
)


def parse_python_module(file_path: Path) -> ast.Module:
    """Parse a Python file into an AST module."""

    return ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))


def check_no_relative_imports(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject relative imports in runtime and script code."""

    violations: list[Violation] = []
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            violations.append(
                Violation(
                    code="SC001",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        "runtime and script modules must use absolute imports, not relative imports"
                    ),
                )
            )
    return violations


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def check_no_internal_reexport_modules(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Reject internal modules that only re-export imports from another module."""

    if not _is_runtime_file(repo_root, file_path):
        return []
    if _is_allowed_reexport_surface(repo_root, file_path):
        return []
    if not _is_pure_reexport_module(module):
        return []
    return [
        Violation(
            code="SC046",
            path=file_path,
            line=1,
            message=(
                "runtime modules must not be pure re-export shims; import from the "
                "implementation module directly or define a real public API surface"
            ),
        )
    ]


def check_no_internal_helper_exports(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Reject __all__ export surfaces inside internal helper packages."""

    if not _is_runtime_file(repo_root, file_path):
        return []
    relative_parts: tuple[str, ...] = file_path.resolve().relative_to(repo_root.resolve()).parts
    if "helpers" not in relative_parts:
        return []

    violations: list[Violation] = []
    for node in module.body:
        if _is_all_assignment(node):
            violations.append(
                Violation(
                    code="SC047",
                    path=file_path,
                    line=getattr(node, "lineno", 1),
                    message=(
                        "internal helper modules must not define __all__; expose public APIs "
                        "from an approved public surface instead"
                    ),
                )
            )
    return violations


def check_source_file_line_count(repo_root: Path, file_path: Path) -> list[Violation]:
    """Reject oversized runtime source files outside explicit backend allowlists."""

    relative_path: Path = file_path.resolve().relative_to(repo_root.resolve())
    relative_text: str = relative_path.as_posix()
    if not relative_text.startswith(_RUNTIME_PREFIX_TEXT):
        return []

    line_count: int = len(file_path.read_text(encoding="utf-8").splitlines())
    if line_count <= _MAX_SOURCE_FILE_LINES:
        return []

    return [
        Violation(
            code="SC048",
            path=file_path,
            line=None,
            message=(
                f"source file exceeds {_MAX_SOURCE_FILE_LINES} lines ({line_count}); "
                "split by concern"
            ),
        )
    ]


def check_helpers_package_layout(repo_root: Path, file_path: Path) -> list[Violation]:
    """Enforce consistent flat-or-subfolder helper package layout."""

    package_dir: Path | None = _role_package_layout_dir(file_path=file_path, package_name="helpers")
    if package_dir is None:
        return []

    return _role_package_layout_violations(
        package_dir=package_dir,
        file_path=file_path,
        package_name="helpers",
        mixed_code="SC049",
        too_many_code="SC050",
        module_label="helper",
        max_flat_modules=_MAX_HELPER_FLAT_MODULES,
        ignored_subfolder_names=frozenset(),
    )


def check_main_package_layout(repo_root: Path, file_path: Path) -> list[Violation]:
    """Enforce consistent flat-or-subfolder main package layout."""

    support_violation: Violation | None = _main_support_folder_violation(
        repo_root=repo_root,
        file_path=file_path,
    )
    package_dir: Path | None = _role_package_layout_dir(file_path=file_path, package_name="main")
    if package_dir is None:
        return [support_violation] if support_violation is not None else []

    violations: list[Violation] = _role_package_layout_violations(
        package_dir=package_dir,
        file_path=file_path,
        package_name="main",
        mixed_code="SC059",
        too_many_code="SC060",
        module_label="entry",
        max_flat_modules=_MAX_MAIN_FLAT_MODULES,
        ignored_subfolder_names=_MAIN_SUPPORT_FOLDER_NAMES,
    )
    if support_violation is not None:
        violations.append(support_violation)
    return violations


def _main_support_folder_violation(*, repo_root: Path, file_path: Path) -> Violation | None:
    relative_path: Path = file_path.resolve().relative_to(repo_root.resolve())
    parts: tuple[str, ...] = relative_path.parts
    index: int
    for index, part in enumerate(parts[:-1]):
        if (
            part == "main"
            and index + 1 < len(parts)
            and parts[index + 1] in _MAIN_SUPPORT_FOLDER_NAMES
        ):
            return Violation(
                code="SC061",
                path=file_path,
                line=None,
                message=(
                    "main package must not contain support folders like helpers/, shared/, "
                    "or classes/; move support code beside main/"
                ),
            )
    return None


def _role_package_layout_violations(
    *,
    package_dir: Path,
    file_path: Path,
    package_name: str,
    mixed_code: str,
    too_many_code: str,
    module_label: str,
    max_flat_modules: int,
    ignored_subfolder_names: frozenset[str],
) -> list[Violation]:
    direct_modules: list[Path] = sorted(
        child
        for child in package_dir.glob("*.py")
        if child.name != "__init__.py" and child.is_file()
    )
    concern_subfolders: list[Path] = sorted(
        child
        for child in package_dir.iterdir()
        if child.is_dir()
        and child.name != "__pycache__"
        and child.name not in ignored_subfolder_names
    )

    violations: list[Violation] = []
    if direct_modules and concern_subfolders:
        violations.append(
            Violation(
                code=mixed_code,
                path=file_path,
                line=None,
                message=(
                    f"{package_name} package mixes flat {module_label} modules with "
                    "concern subfolders; use either flat files or move all modules into "
                    "subfolders"
                ),
            )
        )
    if len(direct_modules) > max_flat_modules:
        violations.append(
            Violation(
                code=too_many_code,
                path=file_path,
                line=None,
                message=(
                    f"{package_name} package has too many direct {module_label} modules "
                    f"({len(direct_modules)} > {max_flat_modules}); organize the "
                    f"entire {package_name} package into concern subfolders consistently, not just "
                    "one file"
                ),
            )
        )
    return violations


def _role_package_layout_dir(*, file_path: Path, package_name: str) -> Path | None:
    if file_path.parent.name == package_name:
        package_dir: Path = file_path.parent
    elif file_path.parent.parent.name == package_name:
        package_dir = file_path.parent.parent
    else:
        return None
    init_file: Path = package_dir / "__init__.py"
    if init_file.exists():
        return package_dir if file_path == init_file else None
    direct_modules: list[Path] = sorted(
        child
        for child in package_dir.glob("*.py")
        if child.name != "__init__.py" and child.is_file()
    )
    if not direct_modules:
        return None
    return package_dir if file_path == direct_modules[0] else None


def check_banned_generic_filename(file_path: Path) -> list[Violation]:
    """Reject vague generic module names in runtime and script code."""

    if file_path.name not in BANNED_GENERIC_FILENAMES:
        return []

    return [
        Violation(
            code="SC003",
            path=file_path,
            line=None,
            message=(
                f"uses banned generic filename '{file_path.name}'; choose a domain-specific name"
            ),
        )
    ]


def check_top_level_domain_role_placement(repo_root: Path, file_path: Path) -> list[Violation]:
    """Reject direct role files or role directories under top-level runtime domains."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) < 4 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []
    if relative_parts[2] == "shared":
        return []

    direct_child_name = relative_parts[3]
    if len(relative_parts) == 4 and direct_child_name in {
        "models.py",
        "types.py",
        "constants.py",
        "exceptions.py",
        "helpers.py",
        "classes.py",
    }:
        return [
            Violation(
                code="SC017",
                path=file_path,
                line=None,
                message=(
                    "top-level runtime domains must not contain direct role files; "
                    "move them into a subpackage"
                ),
            )
        ]

    if len(relative_parts) >= 5 and direct_child_name in _RUNTIME_ROLE_DIRECTORY_NAMES:
        return [
            Violation(
                code="SC017",
                path=file_path,
                line=None,
                message=(
                    "top-level runtime domains must not contain direct role directories such as "
                    "helpers/, classes/, models/, types/, constants/, or exceptions/; "
                    "move them into a subpackage"
                ),
            )
        ]

    return []


def check_top_level_domain_direct_modules(repo_root: Path, file_path: Path) -> list[Violation]:
    """Reject direct modules under top-level runtime domains except role files."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) != 4 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []
    if file_path.name in {
        "__init__.py",
        "models.py",
        "types.py",
        "constants.py",
        "exceptions.py",
        "helpers.py",
    }:
        return []

    return [
        Violation(
            code="SC018",
            path=file_path,
            line=None,
            message=(
                "top-level runtime domains must contain subpackages, not direct modules; "
                "keep direct files limited to role-oriented files like models.py or types.py"
            ),
        )
    ]


def check_nested_runtime_package_direct_modules(
    repo_root: Path, file_path: Path
) -> list[Violation]:
    """Reject ad hoc direct modules in nested runtime packages outside helpers/."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) < 5 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []
    if _is_direct_child_of_main_package(relative_parts):
        return []
    if _is_within_main_package(relative_parts):
        return []
    if any(
        part in {"helpers", "classes", "models", "types", "constants", "exceptions"}
        for part in relative_parts[2:-1]
    ):
        return []
    if file_path.name in {
        "__init__.py",
        "models.py",
        "types.py",
        "constants.py",
        "exceptions.py",
        "helpers.py",
    }:
        return []

    return [
        Violation(
            code="SC027",
            path=file_path,
            line=None,
            message=(
                "nested runtime packages must keep direct files to role-oriented modules; "
                "move additional support code under helpers/"
            ),
        )
    ]


def check_nested_runtime_package_direct_subpackages(
    repo_root: Path, file_path: Path
) -> list[Violation]:
    """Reject arbitrary direct child packages under nested runtime packages."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) < 6 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []
    if _is_within_main_package(relative_parts):
        return []

    allowed_child_names: frozenset[str] = frozenset(
        {
            "helpers",
            "shared",
            "classes",
            "models",
            "types",
            "constants",
            "exceptions",
            "main",
        }
    )
    role_container_names: frozenset[str] = frozenset(
        {"helpers", "classes", "models", "types", "constants", "exceptions"}
    )

    package_parts = relative_parts[2:-1]
    for index in range(2, len(package_parts)):
        parent_package_name = package_parts[index - 1]
        direct_child_name = package_parts[index]
        if parent_package_name in role_container_names:
            continue
        if direct_child_name in allowed_child_names:
            continue
        return [
            Violation(
                code="SC030",
                path=file_path,
                line=1,
                message=(
                    "nested runtime packages must use direct subpackages only for explicit "
                    "support boundaries like helpers/, shared/, classes/, or main/; move "
                    "feature buckets under helpers/ or flatten them into role files"
                ),
            )
        ]
    return []


def check_main_entry_name_collisions(repo_root: Path, file_path: Path) -> list[Violation]:
    """Reject duplicate flat-module and package entry names directly under main/."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) < 6 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []
    if (
        file_path.parent.name != "main"
        or file_path.suffix != ".py"
        or file_path.name == "__init__.py"
    ):
        return []
    if len(relative_parts) < 7 or relative_parts[-3] != "main":
        return []
    if not file_path.with_suffix("").is_dir():
        return []

    return [
        Violation(
            code="SC029",
            path=file_path,
            line=None,
            message=(
                "main/ must not define both a flat module and a package with the same entry "
                "name; choose one entry surface"
            ),
        )
    ]


def check_dev_tooling_location(repo_root: Path, file_path: Path) -> list[Violation]:
    """Reject obvious dev-tooling modules inside the runtime package."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) < 2 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []

    file_stem = file_path.stem
    if file_stem.startswith(DEV_TOOLING_FILE_PREFIXES):
        return [
            Violation(
                code="SC002",
                path=file_path,
                line=None,
                message="dev-only tooling must live under scripts/, not the runtime package",
            )
        ]

    if any(part in DEV_TOOLING_SEGMENTS for part in relative_parts[2:-1]):
        return [
            Violation(
                code="SC002",
                path=file_path,
                line=None,
                message="dev-only tooling must live under scripts/, not the runtime package",
            )
        ]

    return []


def check_helpers_module_name(file_path: Path) -> list[Violation]:
    """Reject helpers.py in favor of a helpers/ package."""

    if file_path.name != "helpers.py":
        return []

    return [
        Violation(
            code="SC004",
            path=file_path,
            line=None,
            message="use a helpers/ package instead of helpers.py",
        )
    ]


def check_classes_module_name(file_path: Path) -> list[Violation]:
    """Reject classes.py in favor of a classes/ package."""

    if file_path.name != "classes.py":
        return []

    return [
        Violation(
            code="SC005",
            path=file_path,
            line=None,
            message="use a classes/ package instead of classes.py",
        )
    ]


def check_classes_package_module_shape(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Require runtime classes/ modules to define exactly one class."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) < 5 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []
    if "classes" not in relative_parts[2:-1] or file_path.name == "__init__.py":
        return []

    class_nodes: list[ast.ClassDef] = [
        node for node in module.body if isinstance(node, ast.ClassDef)
    ]
    if len(class_nodes) == 1:
        return []
    return [
        Violation(
            code="SC043",
            path=file_path,
            line=1,
            message="runtime classes/ modules must define exactly one class",
        )
    ]


def check_init_module(file_path: Path, module: ast.Module) -> list[Violation]:
    """Validate __init__.py contents (nested packages must be docstring-only)."""

    if file_path.name != "__init__.py":
        return []
    if _is_public_surface_module(file_path):
        return []
    if is_docstring_only_module(module):
        return []

    return [
        Violation(
            code="SC006",
            path=file_path,
            line=1,
            message="__init__.py must be empty or docstring-only",
        )
    ]


def check_no_internal_public_surface_imports(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Reject internal imports of the bare public surface package."""

    if not _is_runtime_file(repo_root, file_path):
        return []
    if _is_public_surface_module(file_path):
        return []

    violations: list[Violation] = []
    for node in ast.walk(module):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module == (_RUNTIME_PACKAGE_NAME)
        ):
            violations.append(_public_surface_import_violation(file_path, node.lineno))
            continue
        if isinstance(node, ast.Import) and any(
            alias.name == _RUNTIME_PACKAGE_NAME for alias in node.names
        ):
            violations.append(_public_surface_import_violation(file_path, node.lineno))
    return violations


def _public_surface_import_violation(file_path: Path, line: int) -> Violation:
    return Violation(
        code="SC908",
        path=file_path,
        line=line,
        message=(
            "internal modules must not import from the public surface package; "
            "import from the owning module directly (the top-level surface is for "
            "external consumers only)"
        ),
    )


def check_public_surface_module(file_path: Path, module: ast.Module) -> list[Violation]:
    """Restrict the root public surface to a docstring, imports, and one __all__."""

    if not _is_public_surface_module(file_path):
        return []

    violations: list[Violation] = []
    for node in _non_docstring_body(module):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if _is_all_assignment(node):
            continue
        violations.append(
            Violation(
                code="SC907",
                path=file_path,
                line=getattr(node, "lineno", 1),
                message=(
                    "the public surface package __init__ must contain only re-export imports "
                    "and a single __all__ assignment; move implementation into owning modules"
                ),
            )
        )
    return violations


def check_types_module(file_path: Path, module: ast.Module) -> list[Violation]:
    """Validate types.py contents."""

    if file_path.name != "types.py":
        return []

    violations: list[Violation] = []
    for node in _non_docstring_body(module):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.TypeAlias)):
            continue
        if _is_type_checking_import_block(node):
            continue
        if isinstance(node, ast.ClassDef) and _is_allowed_type_class(node):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            violations.append(
                Violation(
                    code="SC007",
                    path=file_path,
                    line=node.lineno,
                    message="types.py must not define runtime functions",
                )
            )
            continue
        violations.append(
            Violation(
                code="SC007",
                path=file_path,
                line=getattr(node, "lineno", 1),
                message=(
                    "types.py must contain only type-layer declarations such as TypeAlias, "
                    "TypedDict, Protocol, NamedTuple, or Enum"
                ),
            )
        )
    return violations


def check_models_module(file_path: Path, module: ast.Module) -> list[Violation]:
    """Validate models.py contents."""

    if file_path.name != "models.py":
        return []

    violations: list[Violation] = []
    for node in _non_docstring_body(module):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.ClassDef) and _is_allowed_model_class(node):
            if _is_dataclass_class(node) and not _dataclass_is_frozen(node):
                violations.append(
                    Violation(
                        code="SC068",
                        path=file_path,
                        line=node.lineno,
                        message=(
                            "models.py dataclasses must set frozen=True; result models are "
                            "shared across phases and must be immutable"
                        ),
                    )
                )
            continue
        violations.append(
            Violation(
                code="SC008",
                path=file_path,
                line=getattr(node, "lineno", 1),
                message=(
                    "models.py must contain only structured runtime models such as dataclasses "
                    "or pydantic models"
                ),
            )
        )
    return violations


def check_main_public_function_shape(file_path: Path, module: ast.Module) -> list[Violation]:
    """Cap main/ top-level functions so they stay phase-shaped orchestrators."""

    if not _is_main_package_module(file_path):
        return []

    violations: list[Violation] = []
    function_node: ast.FunctionDef | ast.AsyncFunctionDef
    for function_node in _top_level_function_nodes(module):
        function_label: str = (
            "private function" if function_node.name.startswith("_") else "public function"
        )
        statement_count: int = (
            sum(1 for node in ast.walk(function_node) if isinstance(node, ast.stmt)) - 1
        )
        if statement_count > _MAX_MAIN_PUBLIC_FUNCTION_STATEMENTS:
            violations.append(
                Violation(
                    code="SC063",
                    path=file_path,
                    line=function_node.lineno,
                    message=(
                        f"{function_label} '{function_node.name}' has {statement_count} "
                        "statements (main/ limit: 40). "
                        f"{_MAIN_PHASE_REMEDIATION_MESSAGE}"
                    ),
                )
            )

        distinct_calls: int = len(_distinct_callee_names(function_node))
        if distinct_calls > _MAX_MAIN_PUBLIC_FUNCTION_DISTINCT_CALLS:
            violations.append(
                Violation(
                    code="SC064",
                    path=file_path,
                    line=function_node.lineno,
                    message=(
                        f"{function_label} '{function_node.name}' calls {distinct_calls} "
                        "distinct functions (main/ limit: 20). "
                        f"{_MAIN_PHASE_REMEDIATION_MESSAGE}"
                    ),
                )
            )

        local_count: int = len(_assigned_local_names(function_node))
        if local_count > _MAX_MAIN_PUBLIC_FUNCTION_LOCALS:
            violations.append(
                Violation(
                    code="SC065",
                    path=file_path,
                    line=function_node.lineno,
                    message=(
                        f"{function_label} '{function_node.name}' juggles {local_count} "
                        "local variables (main/ limit: 20). This usually means multiple "
                        "phases' intermediate state is interleaved; each extracted phase "
                        "should own its intermediates and return one result model."
                    ),
                )
            )
    return violations


def check_main_discarded_call_results(file_path: Path, module: ast.Module) -> list[Violation]:
    """Require main/ orchestrators to consume phase call results."""

    if not _is_main_package_module(file_path):
        return []

    violations: list[Violation] = []
    function_node: ast.FunctionDef | ast.AsyncFunctionDef
    for function_node in _top_level_function_nodes(module):
        node: ast.AST
        for node in ast.walk(function_node):
            if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
                continue
            if _discarded_call_is_allowed(node.value):
                continue
            violations.append(
                Violation(
                    code="SC066",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        f"result of '{_call_display_name(node.value)}' is discarded in "
                        f"main/ orchestrator '{function_node.name}'. Phases must return "
                        "their effect as a value (assign to a typed local or return it). "
                        "Bare calls are reserved for validators (validate_*/enforce_*/"
                        "check_*), callbacks and progress (on_*/report_*), diagnostics "
                        "(log*/print), and writers (write_*); discard a genuine void "
                        "effect explicitly with '_ = ...'. Do not communicate between "
                        "phases by mutation."
                    ),
                )
            )
    return violations


def check_no_parameter_mutation_in_phase_helpers(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Reject hidden dataflow from mutating function parameters in phase helpers."""

    if not _is_runtime_helpers_module(repo_root=repo_root, file_path=file_path):
        return []

    source_lines: list[str] = file_path.read_text(encoding="utf-8").splitlines()
    violations: list[Violation] = []
    function_node: ast.FunctionDef | ast.AsyncFunctionDef
    for function_node in (
        node
        for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        parameter_names: frozenset[str] = _function_parameter_names(function_node)
        node: ast.AST
        for node in ast.walk(function_node):
            mutated_name: str | None = _parameter_mutated_by_node(
                node=node,
                parameter_names=parameter_names,
            )
            if mutated_name is None:
                continue
            line_number: int = getattr(node, "lineno", function_node.lineno)
            if _line_allows_parameter_mutation(source_lines=source_lines, line_number=line_number):
                continue
            violations.append(
                Violation(
                    code="SC067",
                    path=file_path,
                    line=line_number,
                    message=(
                        f"'{mutated_name}' is a parameter and is mutated here. Helpers should "
                        "accept inputs and return results; mutating arguments hides dataflow "
                        "from callers. Return a new/updated value instead, or mark a deliberate "
                        "builder with '# sc: allow-param-mutation'."
                    ),
                )
            )
    return violations


def check_constants_module(file_path: Path, module: ast.Module) -> list[Violation]:
    """Validate constants.py contents."""

    if file_path.name != "constants.py":
        return []

    violations: list[Violation] = []
    for node in _non_docstring_body(module):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)):
            continue
        violations.append(
            Violation(
                code="SC009",
                path=file_path,
                line=getattr(node, "lineno", 1),
                message=(
                    "constants.py must contain only constant assignments and supporting imports"
                ),
            )
        )
    return violations


def check_model_declarations_outside_models(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject model declarations outside models.py."""

    if file_path.name == "models.py" or _is_within_role_package(file_path, "models"):
        return []

    violations: list[Violation] = []
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef) and _is_allowed_model_class(node):
            violations.append(
                Violation(
                    code="SC014",
                    path=file_path,
                    line=node.lineno,
                    message="structured runtime models must be defined in models.py",
                )
            )
    return violations


def check_no_raw_runtime_diagnostics(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject raw built-in raises and asserts in production runtime code."""

    if not _is_runtime_source_file(file_path):
        return []

    violations: list[Violation] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Raise) and _raise_uses_raw_builtin(node):
            violations.append(
                Violation(
                    code="SC035",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        "production code must raise a structured project error instead of "
                        "a raw built-in exception"
                    ),
                )
            )
        if isinstance(node, ast.Assert):
            violations.append(
                Violation(
                    code="SC036",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        "production code must not use assert for runtime invariants; "
                        "raise a structured project error"
                    ),
                )
            )
    return violations


def check_no_swallowed_exception_probes(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject broad exception handlers that silently answer existence probes."""

    if not _is_runtime_source_file(file_path):
        return []

    violations: list[Violation] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not _is_bare_exception_handler(node):
            continue
        if not _handler_body_is_single_swallow(node.body):
            continue
        violations.append(
            Violation(
                code="SC044",
                path=file_path,
                line=node.lineno,
                message=(
                    "runtime code must not swallow broad exceptions as existence probe "
                    "answers; use adapter metadata checks or log best-effort fallbacks"
                ),
            )
        )
    return violations


def check_single_line_docstrings(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject new multiline docstrings in runtime and script code."""

    violations: list[Violation] = []
    node: ast.AST
    for node in _docstring_bearing_nodes(module):
        if not getattr(node, "body", None):
            continue
        first_statement: ast.stmt = node.body[0]
        if not _statement_is_multiline_docstring(first_statement):
            continue
        violations.append(
            Violation(
                code="SC055",
                path=file_path,
                line=first_statement.lineno,
                message=(
                    "docstrings must be a single line; move extended explanation into docs or tests"
                ),
            )
        )
    return violations


def check_no_standalone_comments(file_path: Path) -> list[Violation]:
    """Reject standalone explanatory comments outside narrow legacy/tooling exceptions."""

    violations: list[Violation] = []
    source: str = file_path.read_text(encoding="utf-8")
    token: tokenize.TokenInfo
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            comment: str = token.string.strip()
            if comment.startswith(_SC056_COMMENT_ALLOWED_PREFIXES):
                continue
            violations.append(
                Violation(
                    code="SC056",
                    path=file_path,
                    line=token.start[0],
                    message=(
                        "standalone comments are not allowed in runtime/script code; prefer clear "
                        "names or a single-line docstring, and use docs/tests for longer context"
                    ),
                )
            )
    except tokenize.TokenError:
        return []
    return violations


def _path_is_allowed(*, path_text: str, allowed_paths: tuple[str, ...]) -> bool:
    return any(path_text.endswith(allowed_path) for allowed_path in allowed_paths)


def _call_base_name(node: ast.Call) -> str | None:
    return _base_name(node.func)


def _docstring_bearing_nodes(module: ast.Module) -> tuple[ast.AST, ...]:
    return (
        module,
        *(node for node in ast.walk(module) if isinstance(node, _DOCSTRING_BEARING_NODE_TYPES)),
    )


def _statement_is_multiline_docstring(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Expr):
        return False
    if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
        return False
    end_lineno: int = getattr(node, "end_lineno", node.lineno)
    return end_lineno > node.lineno or "\n" in node.value.value


def _is_method_definition(*, definition: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current: ast.AST = definition
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.ClassDef):
            return True
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
    return False


def _call_is_inside_loop(*, node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current: ast.AST = node
    while current in parents:
        current = parents[current]
        if isinstance(
            current, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            return True
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
    return False


def check_private_definition_ordering(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject private dataclasses and constants that appear after function definitions."""

    violations: list[Violation] = []
    first_function_line: int | None = None
    node: ast.stmt
    for node in module.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and first_function_line is None
        ):
            first_function_line = node.lineno
        if first_function_line is None:
            continue
        if (
            isinstance(node, ast.ClassDef)
            and node.name.startswith("_")
            and _is_dataclass_class(node)
        ):
            violations.append(
                Violation(
                    code="SC034",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        "private dataclass definitions must appear before "
                        "function definitions at module level"
                    ),
                )
            )
        private_target: str | None = _private_assignment_target(node)
        if private_target is not None:
            violations.append(
                Violation(
                    code="SC034",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        "private constant definitions must appear before "
                        "function definitions at module level"
                    ),
                )
            )
    return violations


def _private_assignment_target(node: ast.stmt) -> str | None:
    """Return the target name if node is a private module-level assignment, else None."""

    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        if node.target.id.startswith("_"):
            return node.target.id
    if isinstance(node, ast.Assign):
        target: ast.expr
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.startswith("_"):
                return target.id
    return None


def check_type_declarations_outside_types(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject type-layer declarations outside types.py."""

    if file_path.name == "types.py" or _is_within_role_package(file_path, "types"):
        return []

    violations: list[Violation] = []
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef) and _is_allowed_type_class(node):
            if node.name.startswith("_") and _is_within_role_package(file_path, "helpers"):
                continue
            violations.append(
                Violation(
                    code="SC015",
                    path=file_path,
                    line=node.lineno,
                    message="type-layer declarations must be defined in types.py",
                )
            )
            continue

        if (
            isinstance(node, ast.TypeAlias)
            and not _is_private_type_alias(node)
            and not _is_local_model_union_alias(
                file_path=file_path,
                module=module,
                node=node,
            )
        ):
            violations.append(
                Violation(
                    code="SC015",
                    path=file_path,
                    line=node.lineno,
                    message="type-layer declarations must be defined in types.py",
                )
            )
            continue

        if _is_newtype_assignment(node):
            violations.append(
                Violation(
                    code="SC015",
                    path=file_path,
                    line=node.lineno,
                    message="type-layer declarations must be defined in types.py",
                )
            )
    return violations


def check_exception_declarations_outside_exceptions(
    file_path: Path, module: ast.Module
) -> list[Violation]:
    """Reject custom exception declarations outside exceptions.py."""

    if file_path.name == "exceptions.py" or _is_within_role_package(file_path, "exceptions"):
        if _is_direct_child_of_helpers_root(file_path):
            return [
                Violation(
                    code="SC021",
                    path=file_path,
                    line=1,
                    message=(
                        "custom exceptions must not live under helpers/; "
                        "define them in a top-level exceptions.py or exceptions/ boundary"
                    ),
                )
            ]
        return []

    violations: list[Violation] = []
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef) and _is_exception_class(node):
            violations.append(
                Violation(
                    code="SC021",
                    path=file_path,
                    line=node.lineno,
                    message="custom exceptions must be defined in exceptions.py or exceptions/",
                )
            )
    return violations


def check_constants_outside_constants(file_path: Path, module: ast.Module) -> list[Violation]:
    """Reject uppercase module-level constant assignments outside constants.py."""

    if file_path.name == "constants.py":
        return []

    violations: list[Violation] = []
    for node in _non_docstring_body(module):
        targets: list[str] = []
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        else:
            continue

        for target_name in targets:
            if target_name.startswith("_"):
                continue
            if target_name.isupper():
                violations.append(
                    Violation(
                        code="SC016",
                        path=file_path,
                        line=node.lineno,
                        message="module-level uppercase constants must be defined in constants.py",
                    )
                )
    return violations


def check_helpers_package_shape(repo_root: Path, file_path: Path) -> list[Violation]:
    """Keep helpers/ shallow and free of generic entrypoints."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if "helpers" not in relative_parts[:-1]:
        return []

    helpers_index = relative_parts.index("helpers")
    if len(relative_parts) == helpers_index + 2 and file_path.name != "main.py":
        return []
    if len(relative_parts) == helpers_index + 3 and file_path.name != "main.py":
        return []

    code: str = "SC010" if len(relative_parts) == helpers_index + 2 else "SC022"
    message: str = (
        "helpers/ must not contain main.py; keep orchestration outside helper packages"
        if code == "SC010"
        else (
            "helper subpackages must stay shallow and use direct role-oriented files; "
            "main.py and nested subpackages are not allowed under scoped helpers"
        )
    )

    return [
        Violation(
            code=code,
            path=file_path,
            line=None,
            message=message,
        )
    ]


def check_shared_package_structure(repo_root: Path, file_path: Path) -> list[Violation]:
    """Reject orchestration entrypoints inside shared/ packages."""

    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).parts
    if "shared" not in relative_parts[:-1]:
        return []
    shared_index = relative_parts.index("shared")
    if (
        len(relative_parts) > shared_index + 2
        and "helpers" in relative_parts[shared_index + 1 : -1]
    ):
        return []
    if file_path.name != "main.py":
        return []

    return [
        Violation(
            code="SC012",
            path=file_path,
            line=None,
            message=(
                "shared/ must not contain main.py; keep shared packages limited to support code"
            ),
        )
    ]


def check_no_sibling_package_imports(
    repo_root: Path,
    file_path: Path,
    module: ast.Module,
) -> list[Violation]:
    """Reject direct imports from sibling subpackages instead of parent shared/."""

    current_package_parts = _subpackage_parts(repo_root, file_path)
    if len(current_package_parts) < 3:
        return []
    if current_package_parts[-1] == "shared":
        return []

    parent_package_parts = current_package_parts[:-1]
    current_subpackage_name = current_package_parts[-1]
    violations: list[Violation] = []

    for node in ast.walk(module):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue

        imported_parts = tuple(node.module.split("."))
        if imported_parts[: len(parent_package_parts)] != parent_package_parts:
            continue
        if len(imported_parts) <= len(parent_package_parts):
            continue
        if _is_within_same_helpers_package(current_package_parts, imported_parts):
            continue

        sibling_name = imported_parts[len(parent_package_parts)]
        if parent_package_parts[-1] == "main" and sibling_name in {"helpers", "shared"}:
            continue
        if sibling_name == "helpers" and current_subpackage_name in {
            "classes",
            "main",
            "models",
            "types",
            "constants",
            "exceptions",
        }:
            continue
        if sibling_name == "classes" and current_subpackage_name == "helpers":
            continue
        if sibling_name == "classes" and current_subpackage_name == "main":
            continue
        if sibling_name in {"shared", current_subpackage_name}:
            continue
        if (
            current_subpackage_name == "entry"
            and parent_package_parts[-1] == "main"
            and imported_parts[-1] == "main"
        ):
            continue
        if len(imported_parts) == len(parent_package_parts) + 1:
            continue
        if _is_allowed_sibling_public_surface(parent_package_parts, imported_parts):
            continue

        violations.append(
            Violation(
                code="SC011",
                path=file_path,
                line=node.lineno,
                message=(
                    "subpackage code must not import sibling package internals; "
                    "the owning sibling must publish it via main/ or role files"
                ),
            )
        )

    for node in ast.walk(module):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            imported_parts = tuple(alias.name.split("."))
            if imported_parts[: len(parent_package_parts)] != parent_package_parts:
                continue
            if len(imported_parts) <= len(parent_package_parts) + 1:
                continue
            if _is_within_same_helpers_package(current_package_parts, imported_parts):
                continue
            if _is_allowed_sibling_public_surface(parent_package_parts, imported_parts):
                continue

            sibling_name = imported_parts[len(parent_package_parts)]
            if parent_package_parts[-1] == "main" and sibling_name in {"helpers", "shared"}:
                continue
            if sibling_name == "helpers" and current_subpackage_name in {
                "classes",
                "main",
                "models",
                "types",
                "constants",
                "exceptions",
            }:
                continue
            if sibling_name == "classes" and current_subpackage_name == "helpers":
                continue
            if sibling_name == "classes" and current_subpackage_name == "main":
                continue
            if sibling_name in {"shared", current_subpackage_name}:
                continue

            violations.append(
                Violation(
                    code="SC011",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        "subpackage code must not import sibling package internals; "
                        f"promote shared code to {'.'.join(parent_package_parts + ('shared',))}"
                    ),
                )
            )

    return violations


def _is_within_same_helpers_package(
    current_package_parts: tuple[str, ...], imported_parts: tuple[str, ...]
) -> bool:
    if "helpers" not in current_package_parts:
        return False
    helpers_index: int = current_package_parts.index("helpers")
    helpers_prefix: tuple[str, ...] = current_package_parts[: helpers_index + 1]
    if imported_parts[: len(helpers_prefix)] != helpers_prefix:
        return False
    return len(current_package_parts) > helpers_index + 1 and len(imported_parts) > len(
        helpers_prefix
    )


def check_shared_package_imports(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Reject shared/ imports that reach into sibling package internals."""

    current_package_parts = _subpackage_parts(repo_root, file_path)
    if len(current_package_parts) < 3 or current_package_parts[-1] != "shared":
        return []

    parent_package_parts = current_package_parts[:-1]
    violations: list[Violation] = []

    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_parts = tuple(node.module.split("."))
            if _is_forbidden_shared_import(parent_package_parts, imported_parts):
                violations.append(
                    Violation(
                        code="SC013",
                        path=file_path,
                        line=node.lineno,
                        message=(
                            "shared/ must not import sibling package internals; "
                            "shared code should stay dependency-neutral"
                        ),
                    )
                )

        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_parts = tuple(alias.name.split("."))
                if _is_forbidden_shared_import(parent_package_parts, imported_parts):
                    violations.append(
                        Violation(
                            code="SC013",
                            path=file_path,
                            line=node.lineno,
                            message=(
                                "shared/ must not import sibling package internals; "
                                "shared code should stay dependency-neutral"
                            ),
                        )
                    )

    return violations


def check_cross_package_internal_imports(
    repo_root: Path,
    file_path: Path,
    module: ast.Module,
) -> list[Violation]:
    """Block imports that reach into another domain package's internal structure."""

    relative_parts: tuple[str, ...] = file_path.resolve().relative_to(repo_root.resolve()).parts
    if len(relative_parts) < 4 or relative_parts[:2] != _RUNTIME_PREFIX:
        return []
    current_domain_parts: tuple[str, ...] = relative_parts[2:]
    current_domain: str = current_domain_parts[0]
    current_subdomain: str | None = (
        current_domain_parts[1] if len(current_domain_parts) > 2 else None
    )

    violations: list[Violation] = []
    _DEEP_INTERNAL_SEGMENTS: frozenset[str] = frozenset({"shared", "helpers"})
    _PUBLIC_MODULES: frozenset[str] = frozenset(
        {"classes", "models", "types", "constants", "exceptions", "__init__", "main"}
    )

    for node in ast.walk(module):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        imported_parts: tuple[str, ...] = tuple(node.module.split("."))
        if len(imported_parts) < 3 or imported_parts[0] != _RUNTIME_PACKAGE_NAME:
            continue

        imported_domain: str = imported_parts[1]
        if imported_domain == current_domain:
            if len(imported_parts) < 4:
                continue
            imported_subdomain: str = imported_parts[2]
            if current_subdomain is not None and imported_subdomain == current_subdomain:
                continue
            if imported_subdomain == "shared":
                continue
            if len(imported_parts) >= 4 and imported_parts[3] in _PUBLIC_MODULES:
                continue
            if len(imported_parts) == 3:
                continue
            if _has_deep_internal_segment(imported_parts[3:], _DEEP_INTERNAL_SEGMENTS):
                violations.append(
                    Violation(
                        code="SC033",
                        path=file_path,
                        line=node.lineno,
                        message=(
                            f"cross-package import reaches into internal structure of "
                            f"'{'.'.join(imported_parts[:3])}'; import from its public "
                            f"surface (classes, models, types, constants, exceptions, or a thin "
                            f"main/ entry module). If the code is helper logic rather than "
                            f"an entrypoint, move it to helpers/ of the owning domain and "
                            f"publish it via main/"
                        ),
                    )
                )
            continue

        if imported_domain == "shared":
            continue

        if len(imported_parts) >= 4:
            target_module: str = imported_parts[2]
            if target_module in _PUBLIC_MODULES:
                continue
            if _has_deep_internal_segment(imported_parts[2:], _DEEP_INTERNAL_SEGMENTS):
                violations.append(
                    Violation(
                        code="SC033",
                        path=file_path,
                        line=node.lineno,
                        message=(
                            f"cross-package import reaches into internal structure of "
                            f"'{'.'.join(imported_parts[:2])}'; import from its public "
                            f"surface (classes, models, types, constants, exceptions, or a thin "
                            f"main/ entry module). If the code is helper logic rather than "
                            f"an entrypoint, move it to helpers/ of the owning domain and "
                            f"publish it via main/"
                        ),
                    )
                )

    return violations


def _has_deep_internal_segment(parts: tuple[str, ...], internal_segments: frozenset[str]) -> bool:
    """Check whether any segment in the import path is a deep internal boundary."""

    return any(seg in internal_segments for seg in parts)


def _is_runtime_file(repo_root: Path, file_path: Path) -> bool:
    relative_parts: tuple[str, ...] = file_path.resolve().relative_to(repo_root.resolve()).parts
    return len(relative_parts) >= 3 and relative_parts[:2] == _RUNTIME_PREFIX


def _is_public_surface_module(file_path: Path) -> bool:
    resolved: Path = file_path.resolve()
    return (
        resolved.name == "__init__.py"
        and resolved.parent.name == _RUNTIME_PACKAGE_NAME
        and resolved.parent.parent.name == _RUNTIME_PREFIX[0]
    )


def _is_allowed_reexport_surface(repo_root: Path, file_path: Path) -> bool:
    relative_parts: tuple[str, ...] = file_path.resolve().relative_to(repo_root.resolve()).parts
    if file_path.name == "__init__.py":
        return True
    if len(relative_parts) == 3 and relative_parts[:2] == _RUNTIME_PREFIX:
        return True
    if len(relative_parts) == 4 and relative_parts[3] == "exceptions.py":
        return True
    return False


def _is_pure_reexport_module(module: ast.Module) -> bool:
    saw_import: bool = False
    saw_all: bool = False
    for node in module.body:
        if _is_module_docstring(node) or _is_future_annotations_import(node):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            saw_import = True
            continue
        if _is_all_assignment(node):
            saw_all = True
            continue
        return False
    return saw_import and saw_all


def _is_module_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_future_annotations_import(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
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


def _is_super_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _is_name(node.func, "super")


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def check_entry_module_shape(file_path: Path, module: ast.Module) -> list[Violation]:
    """Enforce entry modules as focused single-entry surfaces."""

    if not _is_entry_module(file_path):
        return []
    public_function_nodes = [
        node
        for node in _non_docstring_body(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    private_function_nodes = [
        node
        for node in _non_docstring_body(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("_")
    ]
    violations: list[Violation] = []

    if len(public_function_nodes) != 1:
        violations.append(
            Violation(
                code="SC019",
                path=file_path,
                line=1,
                message=("entry modules must define exactly one public top-level function"),
            )
        )

    if len(private_function_nodes) > 2:
        violations.append(
            Violation(
                code="SC026",
                path=file_path,
                line=private_function_nodes[2].lineno,
                message=(
                    "entry modules must define at most two private top-level functions; "
                    "extract additional behavior to sibling modules under main/ or helpers/ "
                    "support code"
                ),
            )
        )

    for node in _non_docstring_body(module):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        violations.append(
            Violation(
                code="SC020",
                path=file_path,
                line=getattr(node, "lineno", 1),
                message="entry modules must contain only imports and top-level functions",
            )
        )

    return violations


def is_docstring_only_module(module: ast.Module) -> bool:
    """Return whether the module body is empty or docstring-only."""

    body = module.body
    if not body:
        return True
    if len(body) != 1:
        return False
    return _is_string_expr(body[0])


def _non_docstring_body(module: ast.Module) -> list[ast.stmt]:
    if module.body and _is_string_expr(module.body[0]):
        return module.body[1:]
    return list(module.body)


def _is_entry_module(file_path: Path) -> bool:
    return (
        file_path.suffix == ".py"
        and file_path.name not in {"__init__.py", "main.py"}
        and file_path.parent.name == "main"
    )


def _is_direct_child_of_helpers_root(file_path: Path) -> bool:
    parts = file_path.parts
    if "helpers" not in parts[:-1]:
        return False
    helpers_index = parts.index("helpers")
    return len(parts) == helpers_index + 2


def _is_string_expr(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_type_checking_import_block(node: ast.stmt) -> bool:
    """Return whether a node is an `if TYPE_CHECKING:` block containing only imports."""

    if not isinstance(node, ast.If):
        return False
    test: ast.expr = node.test
    if isinstance(test, ast.Name):
        test_name: str = test.id
    elif isinstance(test, ast.Attribute):
        test_name = test.attr
    else:
        return False
    if test_name != "TYPE_CHECKING":
        return False
    if node.orelse:
        return False
    return all(isinstance(statement, (ast.Import, ast.ImportFrom)) for statement in node.body)


def _is_allowed_type_class(node: ast.ClassDef) -> bool:
    if _is_dataclass_class(node) or _inherits_from_base_names(node, MODEL_CLASS_BASE_NAMES):
        return False
    return _inherits_from_base_names(node, TYPE_CLASS_BASE_NAMES)


def _is_allowed_model_class(node: ast.ClassDef) -> bool:
    if node.name.startswith("_"):
        return False
    return _is_dataclass_class(node) or _inherits_from_base_names(node, MODEL_CLASS_BASE_NAMES)


def _is_exception_class(node: ast.ClassDef) -> bool:
    """Return whether a class definition looks like a custom exception."""

    if node.name.endswith(("Error", "Exception")):
        return True

    return any(
        (base_name or "").endswith(("Error", "Exception"))
        for base_name in (_base_name(base) for base in node.bases)
    )


def _is_dataclass_class(node: ast.ClassDef) -> bool:
    return any(
        _decorator_name(decorator).endswith("dataclass") for decorator in node.decorator_list
    )


def _dataclass_is_frozen(node: ast.ClassDef) -> bool:
    decorator: ast.expr
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and _decorator_name(decorator.func).endswith(
            "dataclass"
        ):
            keyword: ast.keyword
            for keyword in decorator.keywords:
                if keyword.arg == "frozen" and isinstance(keyword.value, ast.Constant):
                    return keyword.value.value is True
            return False
    return False


def _is_main_package_module(file_path: Path) -> bool:
    return (
        file_path.suffix == ".py"
        and file_path.name != "__init__.py"
        and "main" in file_path.parts[:-1]
    )


def _top_level_function_nodes(
    module: ast.Module,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    return tuple(
        node
        for node in _non_docstring_body(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _distinct_callee_names(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    names: set[str] = set()
    node: ast.AST
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        name: str | None = _call_name(node)
        if name is not None:
            names.add(name)
    return frozenset(names)


def _assigned_local_names(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    names: set[str] = set()
    node: ast.AST
    for node in ast.walk(function_node):
        if isinstance(node, ast.Assign):
            target: ast.expr
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return frozenset(names)


def _discarded_call_is_allowed(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name):
        return True
    name: str = node.func.id.lstrip("_")
    if name in _DISCARDED_CALL_ALLOWED_NAMES:
        return True
    allowed_prefixes: tuple[str, ...] = (
        *_DISCARDED_CALL_VALIDATOR_PREFIXES,
        *_DISCARDED_CALL_CALLBACK_PREFIXES,
        *_DISCARDED_CALL_DIAGNOSTIC_PREFIXES,
        *_DISCARDED_CALL_WRITER_PREFIXES,
    )
    return any(name.startswith(prefix) for prefix in allowed_prefixes)


def _call_display_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        base_name: str | None = _base_name(node.func.value)
        if base_name is None:
            return node.func.attr
        return f"{base_name}.{node.func.attr}"
    return "<call>"


def _function_parameter_names(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> frozenset[str]:
    return frozenset(
        arg.arg
        for arg in (
            *function_node.args.posonlyargs,
            *function_node.args.args,
            *function_node.args.kwonlyargs,
        )
        if arg.arg not in _PARAMETER_MUTATION_EXEMPT_PARAMETERS
    )


def _parameter_mutated_by_node(*, node: ast.AST, parameter_names: frozenset[str]) -> str | None:
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return _parameter_mutated_by_assignment(node=node, parameter_names=parameter_names)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr not in _PARAMETER_MUTATION_METHODS:
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
    target: ast.expr
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


def _line_allows_parameter_mutation(*, source_lines: list[str], line_number: int) -> bool:
    if line_number < 1 or line_number > len(source_lines):
        return False
    return _PARAMETER_MUTATION_ALLOW_COMMENT in source_lines[line_number - 1]


def _inherits_from_base_names(node: ast.ClassDef, base_names: frozenset[str]) -> bool:
    return any(_base_name(base) in base_names for base in node.bases)


def _is_local_model_union_alias(
    *, file_path: Path, module: ast.Module, node: ast.TypeAlias
) -> bool:
    if not _is_within_role_package(file_path, "models"):
        return False

    model_class_names: frozenset[str] = frozenset(
        child.name
        for child in _non_docstring_body(module)
        if isinstance(child, ast.ClassDef) and _is_allowed_model_class(child)
    )
    if not model_class_names:
        return False

    union_member_names: tuple[str, ...] | None = _local_union_member_names(node.value)
    if union_member_names is None:
        return False
    if len(union_member_names) < 2:
        return False
    return all(name in model_class_names for name in union_member_names)


def _is_private_type_alias(node: ast.TypeAlias) -> bool:
    return isinstance(node.name, ast.Name) and node.name.id.startswith("_")


def _local_union_member_names(node: ast.expr) -> tuple[str, ...] | None:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left_names: tuple[str, ...] | None = _local_union_member_names(node.left)
        right_names: tuple[str, ...] | None = _local_union_member_names(node.right)
        if left_names is None or right_names is None:
            return None
        return (*left_names, *right_names)
    return None


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return None


def _is_runtime_helpers_module(*, repo_root: Path, file_path: Path) -> bool:
    relative_parts: tuple[str, ...] = file_path.resolve().relative_to(repo_root.resolve()).parts
    return (
        len(relative_parts) >= 5
        and relative_parts[:2] == _RUNTIME_PREFIX
        and "helpers" in relative_parts[2:-1]
        and file_path.suffix == ".py"
    )


def _is_runtime_source_file(file_path: Path) -> bool:
    parts: tuple[str, ...] = file_path.parts
    return (
        _RUNTIME_PREFIX[0] in parts and _RUNTIME_PACKAGE_NAME in parts and file_path.suffix == ".py"
    )


def _raise_uses_raw_builtin(node: ast.Raise) -> bool:
    if node.exc is None:
        return False
    raised_name: str | None = (
        _base_name(node.exc.func) if isinstance(node.exc, ast.Call) else _base_name(node.exc)
    )
    return raised_name in RAW_BUILTIN_RAISE_NAMES


def _is_bare_exception_handler(node: ast.ExceptHandler) -> bool:
    return node.name is None and isinstance(node.type, ast.Name) and node.type.id == "Exception"


def _handler_body_is_single_swallow(body: list[ast.stmt]) -> bool:
    if len(body) != 1:
        return False

    statement: ast.stmt = body[0]
    if isinstance(statement, ast.Continue):
        return True
    if not isinstance(statement, ast.Return):
        return False
    return _is_swallowed_probe_return_value(statement.value)


def _is_swallowed_probe_return_value(node: ast.expr | None) -> bool:
    if isinstance(node, ast.Constant):
        return node.value is None or node.value is False
    if isinstance(node, ast.Dict):
        return not node.keys and not node.values
    if isinstance(node, ast.Tuple):
        return not node.elts
    return False


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _is_newtype_assignment(node: ast.AST) -> bool:
    value: ast.expr | None = None
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        value = node.value
    elif (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    ):
        value = node.value

    if not isinstance(value, ast.Call):
        return False

    return _base_name(value.func) == "NewType"


def _is_within_role_package(file_path: Path, role_directory_name: str) -> bool:
    return role_directory_name in file_path.parts[:-1]


def _is_direct_child_of_main_package(relative_parts: tuple[str, ...]) -> bool:
    return (
        len(relative_parts) >= 2
        and relative_parts[-2] == "main"
        and relative_parts[-1] != "main.py"
    )


def _is_within_main_package(relative_parts: tuple[str, ...]) -> bool:
    return "main" in relative_parts[2:-1] and relative_parts[-1] != "main.py"


def _subpackage_parts(repo_root: Path, file_path: Path) -> tuple[str, ...]:
    relative_parts = file_path.resolve().relative_to(repo_root.resolve()).with_suffix("").parts

    if len(relative_parts) >= 4 and relative_parts[:2] == _RUNTIME_PREFIX:
        package_parts = relative_parts[1:-1]
    elif len(relative_parts) >= 3 and relative_parts[0] == "scripts":
        package_parts = relative_parts[:-1]
    else:
        return ()

    return tuple(package_parts)


def _is_forbidden_shared_import(
    parent_package_parts: tuple[str, ...],
    imported_parts: tuple[str, ...],
) -> bool:
    if imported_parts[: len(parent_package_parts)] != parent_package_parts:
        return False
    if len(imported_parts) <= len(parent_package_parts):
        return False

    next_segment = imported_parts[len(parent_package_parts)]
    if next_segment == "shared":
        return False

    return len(imported_parts) > len(parent_package_parts) + 1


def _is_allowed_sibling_public_surface(
    parent_package_parts: tuple[str, ...],
    imported_parts: tuple[str, ...],
) -> bool:
    public_surface_names: frozenset[str] = frozenset({"models", "types", "constants", "exceptions"})
    if (
        len(imported_parts) == len(parent_package_parts) + 2
        and imported_parts[len(parent_package_parts)] == "main"
        and imported_parts[-1] != "main"
    ):
        return True
    if (
        len(imported_parts) == len(parent_package_parts) + 3
        and imported_parts[len(parent_package_parts)] == "main"
        and imported_parts[-1] != "main"
    ):
        return True
    if (
        len(imported_parts) == len(parent_package_parts) + 2
        and imported_parts[len(parent_package_parts)] in public_surface_names
    ):
        return True
    if (
        len(imported_parts) == len(parent_package_parts) + 3
        and imported_parts[len(parent_package_parts) + 1] in public_surface_names
    ):
        return True
    if len(imported_parts) != len(parent_package_parts) + 2:
        return False

    public_module_name: str = imported_parts[-1]
    if public_module_name in public_surface_names:
        return True
    if "adapter" in parent_package_parts:
        return True
    return False


def check_no_runtime_imports_from_tooling(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Prevent runtime package code from depending on dev-tooling modules."""

    if not _is_runtime_file(repo_root, file_path):
        return []

    violations: list[Violation] = []
    for node in ast.walk(module):
        imported_roots: list[tuple[str, int]] = []
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            imported_roots.append((node.module.split(".")[0], node.lineno))
        if isinstance(node, ast.Import):
            imported_roots.extend((alias.name.split(".")[0], node.lineno) for alias in node.names)
        for imported_root, line in imported_roots:
            if imported_root == _TOOLING_ROOT_NAME:
                violations.append(
                    Violation(
                        code="SC901",
                        path=file_path,
                        line=line,
                        message=(
                            "runtime package code must not import from dev tooling under "
                            "scripts/; move shared logic into the runtime package"
                        ),
                    )
                )
    return violations


def check_tooling_entrypoint_shape(
    repo_root: Path, file_path: Path, module: ast.Module
) -> list[Violation]:
    """Keep direct scripts/ files as thin argparse entrypoints that delegate."""

    if not _is_tooling_entrypoint_file(repo_root, file_path):
        return []

    violations: list[Violation] = []
    line_count: int = len(file_path.read_text(encoding="utf-8").splitlines())
    if line_count > _MAX_TOOLING_ENTRYPOINT_LINES:
        violations.append(
            Violation(
                code="SC902",
                path=file_path,
                line=None,
                message=(
                    f"script entrypoints must stay under {_MAX_TOOLING_ENTRYPOINT_LINES} lines "
                    f"({line_count}); move implementation into a package under scripts/"
                ),
            )
        )

    for node in module.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name not in _TOOLING_ENTRYPOINT_ALLOWED_FUNCTION_NAMES
        ):
            violations.append(
                Violation(
                    code="SC903",
                    path=file_path,
                    line=node.lineno,
                    message="script entrypoints may define only main() and parse_args()",
                )
            )
        elif isinstance(node, ast.ClassDef):
            violations.append(
                Violation(
                    code="SC904",
                    path=file_path,
                    line=node.lineno,
                    message=(
                        "script entrypoints must not define classes; move implementation "
                        "into a package under scripts/"
                    ),
                )
            )
        elif _is_module_collection_assignment(node):
            violations.append(
                Violation(
                    code="SC905",
                    path=file_path,
                    line=getattr(node, "lineno", 1),
                    message=(
                        "script entrypoints must not define module-level collection "
                        "constants; move them into a package under scripts/"
                    ),
                )
            )
    return violations


def _is_tooling_entrypoint_file(repo_root: Path, file_path: Path) -> bool:
    try:
        relative_parts: tuple[str, ...] = (
            file_path.resolve().relative_to((repo_root / _TOOLING_ROOT_NAME).resolve()).parts
        )
    except ValueError:
        return False
    if file_path.suffix != ".py" or file_path.name == "__init__.py":
        return False
    return len(relative_parts) == 1


def _is_module_collection_assignment(node: ast.stmt) -> bool:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return isinstance(node.value, (ast.List, ast.Set, ast.Dict, ast.Tuple)) or (
            _is_collection_factory_call(node.value)
        )
    return False


def _is_collection_factory_call(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"dict", "frozenset", "list", "set", "tuple"}
    )


def check_no_shared_packages(repo_root: Path, file_path: Path) -> list[Violation]:
    """Reject shared/ packages anywhere in the runtime package (strata bans shared/)."""

    if not _is_runtime_file(repo_root, file_path):
        return []
    relative_parts: tuple[str, ...] = file_path.resolve().relative_to(repo_root.resolve()).parts
    if "shared" not in relative_parts[:-1]:
        return []
    return [
        Violation(
            code="SC906",
            path=file_path,
            line=None,
            message=(
                "shared/ packages are banned; there is no neutral junk-drawer. The owning "
                "domain must publish reusable code via its main/ entry modules or role "
                "files (models/types/constants/exceptions), and consumers import that "
                "public surface"
            ),
        )
    ]
