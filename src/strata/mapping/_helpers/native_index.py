"""Build call-map indexes from native project-function and local-edge facts."""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import cast

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.main.decode_source import decode_python_source
from strata.instrumentation.constants import NATIVE_PARSE_OPERATION, OPERATION_COUNTERS
from strata.mapping.constants import (
    INIT_MODULE_FILE_NAME,
    MAPPING_EXPRESSION_ATTRIBUTE,
    MAPPING_EXPRESSION_NAME,
    MAPPING_EXPRESSION_SUBSCRIPT,
    PROTOCOL_BASE_NAMES,
    QUALIFIED_NAME_SEPARATOR,
)
from strata.mapping.exceptions import MapError
from strata.mapping.models import (
    ClassDefinition,
    ClassReference,
    FunctionDefinition,
    FunctionSyntax,
    ImportView,
    MappingCall,
    MappingExpression,
    MappingParameter,
    MappingStatement,
    ModuleImports,
    ProjectIndex,
    SourceSnapshot,
)

type _RawExpression = tuple[str, str, tuple[str, ...], _RawExpression | None, str | None]
type _RawImport = tuple[str | None, int, tuple[tuple[str, str | None], ...], bool]
type _RawCall = tuple[_RawExpression, int]
type _RawStatement = tuple[
    bool,
    tuple[str, ...],
    str | None,
    _RawExpression | None,
    _RawExpression | None,
    tuple[_RawCall, ...],
]
type _RawFunction = tuple[
    str,
    int,
    str | None,
    tuple[tuple[str, _RawExpression | None], ...],
    _RawExpression | None,
    tuple[_RawStatement, ...],
]
type _RawAttribute = tuple[str, _RawExpression, bool]
type _RawClass = tuple[
    str,
    int,
    tuple[_RawExpression, ...],
    tuple[_RawAttribute, ...],
    tuple[_RawAttribute, ...],
]
type _RawIndex = tuple[
    tuple[_RawImport, ...],
    tuple[_RawImport, ...],
    tuple[_RawFunction, ...],
    tuple[_RawClass, ...],
]


def build_file_index(*, snapshot: SourceSnapshot) -> ProjectIndex:
    """Parse and project one mapping source through the native backend."""

    return build_file_indexes(snapshots=(snapshot,))[0]


def build_file_indexes(*, snapshots: tuple[SourceSnapshot, ...]) -> tuple[ProjectIndex, ...]:
    """Parse mapping sources in one native parallel batch."""

    return _build_file_indexes(snapshots=snapshots, declarations_only=False)


def build_declaration_indexes(*, snapshots: tuple[SourceSnapshot, ...]) -> tuple[ProjectIndex, ...]:
    """Parse only declaration metadata needed for map cache publication."""

    return _build_file_indexes(snapshots=snapshots, declarations_only=True)


def _build_file_indexes(
    *, snapshots: tuple[SourceSnapshot, ...], declarations_only: bool
) -> tuple[ProjectIndex, ...]:
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    decoded: list[str] = []
    for snapshot in snapshots:
        try:
            decoded.append(decode_python_source(path=snapshot.path, content=snapshot.source))
        except Exception as error:
            message: str = getattr(error, "message", str(error))
            raise MapError(f"Could not parse {snapshot.path}: {message}") from error
    for _ in snapshots:
        OPERATION_COUNTERS.record(operation=NATIVE_PARSE_OPERATION)
    programs: list[object | None] = native.parse_programs(
        decoded, sys.version_info[0], sys.version_info[1]
    )
    indexes: list[ProjectIndex] = []
    for snapshot, source, program in zip(snapshots, decoded, programs, strict=True):
        if program is None:
            try:
                _ = native.parse_program(source, sys.version_info[0], sys.version_info[1])
            except ValueError as error:
                raise MapError(f"Could not parse {snapshot.path}: {error}") from error
            raise MapError(f"Could not parse {snapshot.path}: native parser rejected source")
        raw_facts: object = (
            native.mapping_declaration_facts(program)
            if declarations_only
            else native.mapping_index_facts(program)
        )
        raw: _RawIndex = cast(_RawIndex, raw_facts)
        indexes.append(_project_index(snapshot=snapshot, raw=raw))
    return tuple(indexes)


def _project_index(*, snapshot: SourceSnapshot, raw: _RawIndex) -> ProjectIndex:
    runtime_rows, annotation_rows, function_rows, class_rows = raw
    imports: ModuleImports = ModuleImports(
        runtime=_import_view(
            rows=runtime_rows,
            module_name=snapshot.module_name,
            package_module=snapshot.path.name == INIT_MODULE_FILE_NAME,
        ),
        annotation=_import_view(
            rows=annotation_rows,
            module_name=snapshot.module_name,
            package_module=snapshot.path.name == INIT_MODULE_FILE_NAME,
        ),
    )
    functions: dict[str, FunctionDefinition] = {}
    for row in function_rows:
        name, line, owning_class, parameter_rows, returns, statement_rows = row
        parameters: tuple[MappingParameter, ...] = tuple(
            MappingParameter(parameter_name, _expression(annotation))
            for parameter_name, annotation in parameter_rows
        )
        statements: tuple[MappingStatement, ...] = tuple(
            _statement(statement) for statement in statement_rows
        )
        definition: FunctionDefinition = FunctionDefinition(
            module_name=snapshot.module_name,
            name=name,
            path=snapshot.path,
            syntax=FunctionSyntax(
                line=line,
                parameters=parameters,
                returns=_expression(returns),
                statements=statements,
            ),
            imports=imports,
            owning_class=owning_class,
        )
        functions[definition.key] = definition
    classes: dict[str, ClassDefinition] = {}
    for row in class_rows:
        name, _, raw_bases, class_attributes, instance_attributes = row
        bases: tuple[MappingExpression, ...] = tuple(
            cast(MappingExpression, _expression(base)) for base in raw_bases
        )
        class_definition: ClassDefinition = ClassDefinition(
            module_name=snapshot.module_name,
            name=name,
            path=snapshot.path,
            imports=imports,
            bases=bases,
            base_keys=tuple(
                key
                for base in bases
                if (key := _base_key(base=base, module_name=snapshot.module_name, imports=imports))
                is not None
            ),
            protocol=_is_protocol(bases=bases, imports=imports),
            class_attributes=_attributes(class_attributes),
            instance_attributes=_attributes(instance_attributes),
        )
        classes[class_definition.key] = class_definition
    return ProjectIndex(
        functions=functions,
        classes=classes,
        protocol_implementations=ProjectIndex.build_protocol_implementation_keys(
            class_bases={key: definition.base_keys for key, definition in classes.items()},
            protocol_keys=frozenset(
                key for key, definition in classes.items() if definition.protocol
            ),
        ),
    )


def _expression(raw: _RawExpression | None) -> MappingExpression | None:
    if raw is None:
        return None
    kind, spelling, parts, child, string_value = raw
    return MappingExpression(
        kind=kind,
        spelling=spelling,
        parts=tuple(parts),
        child=_expression(child),
        string_value=string_value,
    )


def _statement(raw: _RawStatement) -> MappingStatement:
    control_flow, assigned_names, binding_name, annotation, value, calls = raw
    return MappingStatement(
        control_flow=control_flow,
        assigned_names=frozenset(assigned_names),
        binding_name=binding_name,
        binding_annotation=_expression(annotation),
        binding_value=_expression(value),
        calls=tuple(
            MappingCall(callee=cast(MappingExpression, _expression(callee)), line=line)
            for callee, line in calls
        ),
    )


def _attributes(rows: tuple[_RawAttribute, ...]) -> dict[str, ClassReference]:
    return {
        name: ClassReference(
            expression=cast(MappingExpression, _expression(expression)), annotation=annotation
        )
        for name, expression, annotation in rows
    }


def _import_view(
    *, rows: tuple[_RawImport, ...], module_name: str, package_module: bool
) -> ImportView:
    symbols: dict[str, tuple[str, str]] = {}
    modules: dict[str, str] = {}
    for module, level, aliases, from_import in rows:
        if from_import:
            imported_from: str | None = _import_from_module(
                imported_module=module,
                level=level,
                module_name=module_name,
                package_module=package_module,
            )
            if imported_from is None:
                continue
            for name, asname in aliases:
                local_name: str = asname or name
                symbols[local_name] = (imported_from, name)
                modules[local_name] = f"{imported_from}.{name}"
            continue
        for name, asname in aliases:
            modules[asname or name.split(QUALIFIED_NAME_SEPARATOR, maxsplit=1)[0]] = name
    return ImportView(symbols=symbols, modules=modules)


def _import_from_module(
    *,
    imported_module: str | None,
    level: int,
    module_name: str,
    package_module: bool,
) -> str | None:
    if level == 0:
        return imported_module
    package_parts: list[str] = module_name.split(QUALIFIED_NAME_SEPARATOR)
    if not package_module:
        package_parts = package_parts[:-1]
    parent_count: int = level - 1
    if parent_count > len(package_parts):
        return None
    base_parts: list[str] = package_parts[: len(package_parts) - parent_count]
    if imported_module is not None:
        base_parts.extend(imported_module.split(QUALIFIED_NAME_SEPARATOR))
    return QUALIFIED_NAME_SEPARATOR.join(base_parts) or None


def _base_key(*, base: MappingExpression, module_name: str, imports: ModuleImports) -> str | None:
    if base.kind == MAPPING_EXPRESSION_SUBSCRIPT and base.child is not None:
        return _base_key(base=base.child, module_name=module_name, imports=imports)
    if base.kind == MAPPING_EXPRESSION_NAME:
        imported: tuple[str, str] | None = imports.runtime.symbols.get(base.name)
        if imported is not None:
            return f"{imported[0]}.{imported[1]}"
        return f"{module_name}.{base.name}"
    if base.kind == MAPPING_EXPRESSION_ATTRIBUTE:
        spelling: str = QUALIFIED_NAME_SEPARATOR.join(base.parts)
        first, separator, remainder = spelling.partition(QUALIFIED_NAME_SEPARATOR)
        imported_module: str | None = imports.runtime.modules.get(first)
        if separator and imported_module is not None:
            return f"{imported_module}.{remainder}"
        return spelling
    return None


def _is_protocol(*, bases: tuple[MappingExpression, ...], imports: ModuleImports) -> bool:
    for base in bases:
        expression: MappingExpression = (
            base.child if base.kind == MAPPING_EXPRESSION_SUBSCRIPT and base.child else base
        )
        spelling: str = QUALIFIED_NAME_SEPARATOR.join(expression.parts)
        if (
            expression.kind == MAPPING_EXPRESSION_NAME
            and expression.name in imports.runtime.symbols
        ):
            imported: tuple[str, str] = imports.runtime.symbols[expression.name]
            spelling = f"{imported[0]}.{imported[1]}"
        elif expression.kind == MAPPING_EXPRESSION_ATTRIBUTE and expression.child is not None:
            module: str | None = imports.runtime.modules.get(expression.child.name)
            if module is not None:
                spelling = f"{module}.{expression.name}"
        if spelling in PROTOCOL_BASE_NAMES:
            return True
    return False
