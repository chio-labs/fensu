"""Public-API custom equivalents of native file-local role policies."""

from __future__ import annotations

import ast
import re

from fensu import (
    Family,
    Fault,
    ModuleDeclarationFacts,
    ModuleStatementFact,
    RuleContext,
    ScopeName,
    Threshold,
    rule,
)
from fensu.rules.catalog.main._get_rule_constraint import get_rule_constraint
from fensu.rules.catalog.main._get_rule_limit import get_rule_limit
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule

_CLASSES: str = "classes"
_CLASSES_FILE: str = "classes.py"
_CONSTANTS: str = "constants"
_EXCEPTIONS: str = "exceptions"
_HELPERS: str = "_helpers"
_HELPERS_FILE: str = "helpers.py"
_INIT: str = "__init__.py"
_IMPORT_STATEMENT_KIND: str = "import statement"
_MAIN: str = "main"
_MAIN_FILE: str = "main.py"
_MINIMUM_NESTED_MODULE_PARTS: int = 3
_MINIMUM_NESTED_SUBPACKAGE_PARTS: int = 4
_MODELS: str = "models"
_NONEXECUTING_IMPORT_GUARD_KIND: str = "nonexecuting import guard"
_PYTHON_SUFFIX: str = ".py"
_COMMAND_FUNCTION_KIND: str = "command function"
_TOP_LEVEL_ROLE_PARTS: int = 2
_TYPES: str = "types"
_RULE_CODE: re.Pattern[str] = re.compile(r"(?:FF[A-Z][0-9]{3}|X[A-Z]*[0-9]+)")


def _excluded_scope(ctx: RuleContext) -> bool:
    return ctx.scope() is ScopeName.TEST


def _direct_tooling_entrypoint(ctx: RuleContext) -> bool:
    return (
        ctx.scope() is ScopeName.TOOLING
        and len(ctx.relative_parts()) == 1
        and ctx.path.suffix == _PYTHON_SUFFIX
        and ctx.path.name != _INIT
    )


@equivalent_rule(
    core_code="FFR001",
    code="XCR001",
    slug="models-only-models-equivalent",
)
def models_only_models_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() != _MODELS:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement and not fact.model_class
    ]


@rule(
    code="XCR002",
    family=Family.CUSTOM,
    slug="types-only-types-equivalent",
    message="types role files may contain only type-layer declarations",
    remediation="Move runtime values and functions out of types.py into their owning runtime role.",
)
def types_only_types_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() != _TYPES:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement
        and not fact.assignment_statement
        and not fact.explicit_type_alias
        and not fact.type_checking_import_block
        and not fact.type_class
    ]


@rule(
    code="XCR003",
    family=Family.CUSTOM,
    slug="constants-only-constants-equivalent",
    message="constants role files may contain only assignments and imports",
    remediation="Move functions and classes out of constants.py into their owning role module.",
)
def constants_only_constants_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() != _CONSTANTS:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement and not fact.assignment_statement
    ]


@rule(
    code="XCR004",
    family=Family.CUSTOM,
    slug="exceptions-only-exceptions-equivalent",
    message="exceptions role files may contain only custom exceptions",
    remediation="Move non-exception declarations out of exceptions.py into their owning role.",
)
def exceptions_only_exceptions_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() != _EXCEPTIONS:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement and not fact.exception_class
    ]


@rule(
    code="XCR101",
    family=Family.CUSTOM,
    slug="model-declaration-outside-models-equivalent",
    message="structured runtime models must be defined in the models role",
    remediation="Move the dataclass or structured model into the owning models.py file.",
)
def model_declaration_outside_models_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() == _MODELS:
        return []
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.module_declarations().model_locations
    ]


@rule(
    code="XCR102",
    family=Family.CUSTOM,
    slug="type-declaration-outside-types-equivalent",
    message="type-layer declarations must be defined in the types role",
    remediation="Move the protocol, enum, TypedDict, or public type alias into types.py.",
)
def type_declaration_outside_types_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() == _TYPES:
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().type_declarations
        if not fact.private
        or ctx.role_of() not in ctx.constraint(name="allowed_private_type_roles")
    ]


@rule(
    code="XCR103",
    family=Family.CUSTOM,
    slug="constant-outside-constants-equivalent",
    message="public uppercase constants must be defined in the constants role",
    remediation="Move the public constant into constants.py and import it from there.",
)
def constant_outside_constants_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() == _CONSTANTS:
        return []
    faults: list[Fault] = []
    for fact in ctx.facts.module_declarations().statements:
        for name in fact.assignment_target_names:
            if not name.startswith("_") and name.isupper():
                faults.append(ctx.fault_at(location=fact.location))
    return faults


@rule(
    code="XCR104",
    family=Family.CUSTOM,
    slug="exception-declaration-outside-exceptions-equivalent",
    message="custom exceptions must be defined in the exceptions role",
    remediation="Move the exception class into the owning exceptions.py file.",
)
def exception_declaration_outside_exceptions_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.role_of() == _EXCEPTIONS:
        return []
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.module_declarations().exception_locations
    ]


@equivalent_rule(
    core_code="FFR201",
    code="XCR201",
    slug="banned-generic-filename-equivalent",
)
def banned_generic_filename_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    forbidden_names: tuple[str, ...] = get_rule_constraint(
        code="FFR201", name="forbidden_module_filenames"
    )
    if _excluded_scope(ctx) or ctx.path.name not in forbidden_names:
        return []
    return [ctx.path_fault(message=f"{ctx.path.name} hides the module's purpose")]


@rule(
    code="XCR202",
    family=Family.CUSTOM,
    slug="helpers-module-name-equivalent",
    message="use an _helpers package instead of helpers.py",
    remediation="Replace helpers.py with an _helpers/ package of specifically named modules.",
)
def helpers_module_name_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.path.name != _HELPERS_FILE:
        return []
    return [ctx.path_fault(message="use an _helpers/ package")]


@rule(
    code="XCR203",
    family=Family.CUSTOM,
    slug="classes-module-name-equivalent",
    message="use a classes package instead of classes.py",
    remediation="Replace classes.py with a classes/ package containing one class per module.",
)
def classes_module_name_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.path.name != _CLASSES_FILE:
        return []
    return [ctx.path_fault(message="use a classes/ package")]


@rule(
    code="XCR205",
    family=Family.CUSTOM,
    slug="helpers-classes-file-private-equivalent",
    message="plain classes in _helpers modules must be file-private",
    remediation="Prefix a file-local helper class with _, or move a shared class into classes/.",
)
def helpers_classes_file_private_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or not ctx.in_role("helpers"):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.module_declarations().statements
        if fact.class_name is not None
        and not fact.class_name.startswith("_")
        and not fact.model_class
        and not fact.type_class
    ]


@equivalent_rule(
    core_code="FFR303",
    code="XCR303",
    slug="helpers-reserved-role-filenames-equivalent",
)
def helpers_reserved_role_filenames_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    reserved_role_filenames: tuple[str, ...] = get_rule_constraint(
        code="FFR303", name="reserved_role_filenames"
    )
    if (
        _excluded_scope(ctx)
        or _HELPERS not in ctx.relative_parts()[:-1]
        or ctx.path.name not in reserved_role_filenames
    ):
        return []
    return [
        ctx.path_fault(
            message=f"reserved role filename '{ctx.path.name}' cannot be nested beneath {_HELPERS}/"
        )
    ]


@equivalent_rule(
    core_code="FFR304",
    code="XCR304",
    slug="nested-direct-modules-equivalent",
)
def nested_direct_modules_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    role_directories: tuple[str, ...] = get_rule_constraint(
        code="FFR304", name="recognized_role_directories"
    )
    role_filenames: tuple[str, ...] = get_rule_constraint(
        code="FFR304", name="recognized_role_filenames"
    )
    if (
        _excluded_scope(ctx)
        or ctx.scope() is ScopeName.TOOLING
        or len(parts) < _MINIMUM_NESTED_MODULE_PARTS
        or _MAIN in parts[:-1]
        or any(part in role_directories for part in parts[:-1])
        or parts[-1] == _INIT
        or parts[-1] in role_filenames
    ):
        return []
    return [ctx.path_fault(message="nested packages must move support code under _helpers/")]


@equivalent_rule(
    core_code="FFR305",
    code="XCR305",
    slug="nested-direct-subpackages-equivalent",
)
def nested_direct_subpackages_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    package_parts: tuple[str, ...] = parts[:-1]
    role_directories: tuple[str, ...] = get_rule_constraint(
        code="FFR305", name="recognized_role_directories"
    )
    if (
        _excluded_scope(ctx)
        or ctx.scope() is ScopeName.TOOLING
        or len(parts) < _MINIMUM_NESTED_SUBPACKAGE_PARTS
        or _MAIN in package_parts
        or _HELPERS in package_parts
    ):
        return []
    for index in range(2, len(package_parts)):
        if package_parts[index - 1] in role_directories or package_parts[index] in role_directories:
            continue
        return [ctx.path_fault(message="nested packages must use explicit role boundaries")]
    return []


@equivalent_rule(
    core_code="FFR307",
    code="XCR307",
    slug="top-level-direct-modules-equivalent",
)
def top_level_direct_modules_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    role_filenames: tuple[str, ...] = get_rule_constraint(
        code="FFR307", name="recognized_role_filenames"
    )
    if (
        _excluded_scope(ctx)
        or ctx.scope() is ScopeName.TOOLING
        or len(parts) != _TOP_LEVEL_ROLE_PARTS
        or parts[-1] == _INIT
        or parts[-1] in role_filenames
    ):
        return []
    return [ctx.path_fault(message="top-level domains must not contain ad hoc direct modules")]


@equivalent_rule(
    core_code="FFR401",
    code="XCR401",
    slug="entry-module-shape-equivalent",
)
def entry_module_shape_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or not ctx.is_entry_module():
        return []
    statements: tuple[ModuleStatementFact, ...] = ctx.facts.module_declarations().statements
    public_functions: tuple[ModuleStatementFact, ...] = tuple(
        fact for fact in statements if fact.function_name and not fact.function_name.startswith("_")
    )
    private_functions: tuple[ModuleStatementFact, ...] = tuple(
        fact for fact in statements if fact.function_name and fact.function_name.startswith("_")
    )
    required_public_functions: int = get_rule_limit(code="FFR401", name="required_public_functions")
    maximum_private_functions: int = get_rule_limit(code="FFR401", name="maximum_private_functions")
    faults: list[Fault] = []
    if len(public_functions) != required_public_functions:
        faults.append(ctx.path_fault(message="entry modules need one public function"))
    if len(private_functions) > maximum_private_functions:
        faults.append(
            ctx.fault_at(
                location=private_functions[maximum_private_functions].location,
                message="main/ entry modules may define at most two private glue functions",
            )
        )
    faults.extend(
        ctx.fault_at(
            location=fact.location,
            message="main/ entry modules may contain only imports and top-level functions",
        )
        for fact in statements
        if not fact.import_statement and fact.function_name is None
    )
    return faults


@rule(
    code="XCR402",
    family=Family.CUSTOM,
    slug="init-module-empty-equivalent",
    message="nested __init__.py files must be empty or docstring-only",
    remediation="Remove runtime declarations and import from the concrete owning module instead.",
)
def init_module_empty_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if (
        _excluded_scope(ctx)
        or ctx.path.name != _INIT
        or len(ctx.relative_parts()) == 1
        or ctx.facts.module_declarations().empty_or_docstring_only
    ):
        return []
    return [ctx.path_fault(message="nested __init__.py must be empty")]


@rule(
    code="XCR403",
    family=Family.CUSTOM,
    slug="no-reexport-shim-equivalent",
    message="internal modules must not exist only to re-export imports",
    remediation=(
        "Import the implementation module directly or expose a deliberate API through an approved "
        "public surface."
    ),
)
def no_reexport_shim_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if (
        _excluded_scope(ctx)
        or ctx.path.name == _INIT
        or ctx.role_of() in ctx.constraint(name="exempt_roles")
        or not ctx.facts.module_declarations().pure_reexport
    ):
        return []
    return [ctx.path_fault(message="internal modules must not be re-export shims")]


@rule(
    code="XCR404",
    family=Family.CUSTOM,
    slug="no-internal-helper-exports-equivalent",
    message="_helpers/ modules must not publish an __all__ surface",
    remediation=(
        "Keep _helpers/ internal and expose public behavior through main/, classes/, models, "
        "types, constants, or exceptions."
    ),
)
def no_internal_helper_exports_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or not ctx.in_role("helpers"):
        return []
    return [
        ctx.fault_at(location=location)
        for location in ctx.facts.module_declarations().all_assignment_locations
    ]


@rule(
    code="XCR406",
    family=Family.CUSTOM,
    slug="public-surface-shape-equivalent",
    message="root package surfaces may contain only imports and one __all__ declaration",
    remediation=(
        "Move runtime behavior into an owning module and keep the root __init__.py as a deliberate "
        "import surface."
    ),
)
def public_surface_shape_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx) or ctx.path.name != _INIT or len(ctx.relative_parts()) != 1:
        return []
    faults: list[Fault] = []
    saw_all: bool = False
    for fact in ctx.facts.module_declarations().statements:
        if fact.docstring_statement or fact.import_statement:
            continue
        if fact.all_assignment:
            if saw_all:
                faults.append(
                    ctx.fault_at(
                        location=fact.location, message="public surface may define __all__ once"
                    )
                )
            saw_all = True
            continue
        faults.append(ctx.fault_at(location=fact.location))
    return faults


@rule(
    code="XCR501",
    family=Family.CUSTOM,
    slug="classes-one-class-per-module-equivalent",
    message="classes/ modules must define exactly one top-level class",
    remediation="Split additional classes into separately named modules under classes/.",
)
def classes_one_class_per_module_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if (
        _excluded_scope(ctx)
        or not ctx.in_role(_CLASSES)
        or ctx.path.name == _INIT
        or ctx.facts.module_declarations().top_level_class_count == 1
    ):
        return []
    return [ctx.path_fault(message="classes modules must define one class")]


@rule(
    code="XCR502",
    family=Family.CUSTOM,
    slug="helpers-package-shape-equivalent",
    message="_helpers/ packages must contain no main.py orchestration entrypoints",
    remediation=(
        "Move main.py orchestration into the sibling main/ role; helper depth is enforced by "
        "FFR301."
    ),
)
def helpers_package_shape_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if (
        _excluded_scope(ctx)
        or _HELPERS not in ctx.relative_parts()[:-1]
        or ctx.path.name != _MAIN_FILE
    ):
        return []
    return [ctx.path_fault(message="_helpers/ packages must not contain main.py orchestration")]


@rule(
    code="XCR601",
    family=Family.CUSTOM,
    slug="source-file-line-count-equivalent",
    message="source files must stay below the configured line limit",
    remediation=(
        "Split the file by a cohesive role or concern instead of extracting arbitrary numbered "
        "fragments."
    ),
)
def source_file_line_count_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if _excluded_scope(ctx):
        return []
    line_count: int = len(ctx.source.splitlines())
    if line_count <= ctx.threshold(name=Threshold.MAX_FILE_LINES):
        return []
    return [ctx.path_fault(message=f"source file has {line_count} lines")]


@equivalent_rule(
    core_code="FFR701",
    code="XCR701",
    slug="tooling-entrypoint-shape-equivalent",
)
def tooling_entrypoint_shape_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if not _direct_tooling_entrypoint(ctx):
        return []
    statements: tuple[ModuleStatementFact, ...] = ctx.facts.module_declarations().statements
    allowed_functions: tuple[str, ...] = get_rule_constraint(
        code="FFR701", name="allowed_command_functions"
    )
    allowed_statement_kinds: tuple[str, ...] = get_rule_constraint(
        code="FFR701", name="allowed_top_level_statement_kinds"
    )
    main_functions: tuple[ModuleStatementFact, ...] = tuple(
        fact for fact in statements if fact.function_name == _MAIN
    )
    required_main_functions: int = get_rule_limit(code="FFR701", name="required_main_functions")
    faults: list[Fault] = []
    if len(main_functions) != required_main_functions:
        faults.append(
            ctx.path_fault(message="direct scripts must define exactly one public main() function")
        )
    for fact in statements:
        if fact.import_statement and _IMPORT_STATEMENT_KIND in allowed_statement_kinds:
            continue
        if fact.function_name is not None:
            if (
                _COMMAND_FUNCTION_KIND in allowed_statement_kinds
                and fact.function_name in allowed_functions
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
        if not fact.nonexecuting_import_guard or (
            _NONEXECUTING_IMPORT_GUARD_KIND not in allowed_statement_kinds
        ):
            faults.append(
                ctx.fault_at(
                    location=fact.location,
                    message=(
                        "direct scripts may contain only imports, command functions, and guards"
                    ),
                )
            )
    return faults


@equivalent_rule(
    core_code="FFR702",
    code="XCR702",
    slug="tooling-entrypoint-delegation-equivalent",
)
def tooling_entrypoint_delegation_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    if not _direct_tooling_entrypoint(ctx):
        return []
    facts: ModuleDeclarationFacts = ctx.facts.module_declarations()
    if not any(fact.function_name == _MAIN for fact in facts.statements):
        return [
            ctx.path_fault(
                message="direct scripts must import and call an entry function from a main/ module"
            )
        ]
    imported_entries: frozenset[str] = (
        facts.imported_main_entry_names
        if _MAIN in ctx.constraint(name="allowed_imported_entry_roles")
        else frozenset()
    )
    faults: list[Fault] = []
    if not any(call.name in imported_entries for call in facts.main_calls):
        faults.append(
            ctx.path_fault(
                message="direct scripts must import and call an entry function from a main/ module"
            )
        )
    allowed_calls: frozenset[str] = frozenset(
        {
            *imported_entries,
            *ctx.constraint(name="allowed_local_main_call_targets"),
        }
    )
    faults.extend(
        ctx.fault_at(
            location=call.location,
            message="direct script main() may call only _parse_args() and imported main/ entries",
        )
        for call in facts.main_calls
        if call.name not in allowed_calls
    )
    return faults


@rule(
    code="XCR703",
    family=Family.CUSTOM,
    slug="tooling-entrypoint-line-count-equivalent",
    message="direct scripts must stay below the configured line limit",
    remediation="Move command implementation into a named tooling or runtime package.",
)
def tooling_entrypoint_line_count_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    if not _direct_tooling_entrypoint(ctx):
        return []
    line_count: int = len(ctx.source.splitlines())
    limit: int = ctx.threshold(name=Threshold.MAX_SCRIPT_ENTRYPOINT_LINES)
    if line_count <= limit:
        return []
    return [ctx.path_fault(message=f"direct script has {line_count} lines (limit: {limit})")]


@rule(
    code="XCR704",
    family=Family.CUSTOM,
    slug="rules-role-content-equivalent",
    message="tooling rules/ modules may contain only decorated rule declarations",
    remediation=(
        "Keep imports and @rule functions here; move supporting implementation into _helpers/, "
        "classes/, models.py, types.py, constants.py, or exceptions.py."
    ),
)
def rules_role_content_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if ctx.scope() is not ScopeName.TOOLING or not ctx.in_role("rules") or ctx.path.name == _INIT:
        return []
    return [
        ctx.fault_at(
            location=fact.location,
            message="rules/ modules may contain only imports and @rule functions",
        )
        for fact in ctx.facts.module_declarations().statements
        if not fact.import_statement
        and not fact.type_checking_import_block
        and not fact.rule_decorated_function
    ]


@rule(
    code="XCR706",
    family=Family.CUSTOM,
    slug="descriptive-rule-module-names-equivalent",
    message="rule module filenames must describe their policy rather than repeat one rule code",
    remediation=(
        "Rename the module after the policy or rule family it implements, using a name such as "
        "conditional_test_flow.py instead of fft104.py."
    ),
)
def descriptive_rule_module_names_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    del module
    if (
        _excluded_scope(ctx)
        or not ctx.in_role("rules")
        or _RULE_CODE.fullmatch(ctx.path.stem.upper()) is None
    ):
        return []
    return [
        ctx.path_fault(
            message="rule module filenames must describe their policy, not repeat a rule code"
        )
    ]
