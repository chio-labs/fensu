"""Index project functions and statically resolvable imports."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.analysis.exceptions import PythonSourceParseError
from strata.analysis.main.parse_source import parse_python_source
from strata.analysis.types import PythonSourceArtifact
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.mapping.constants import (
    EXCLUDED_DIRECTORY_NAMES,
    INIT_MODULE_FILE_NAME,
    INIT_MODULE_NAME,
    PATH_SYMBOL_SEPARATOR,
    POSIX_PATH_SEPARATOR,
    PROPERTY_DECORATOR_NAMES,
    PROTOCOL_BASE_NAMES,
    QUALIFIED_NAME_SEPARATOR,
    SELF_RECEIVER_NAME,
    TYPE_CHECKING_NAMES,
    WINDOWS_PATH_SEPARATOR,
)
from strata.mapping.exceptions import MapError
from strata.mapping.models import (
    ClassDefinition,
    ClassReference,
    FunctionDefinition,
    ImportView,
    MappingSource,
    ModuleImports,
    ProjectIndex,
    SourceSnapshot,
)


def build_project_index(*, sources: tuple[MappingSource, ...]) -> ProjectIndex:
    """Parse project sources once and index top-level classes and callables."""

    functions: dict[str, FunctionDefinition] = {}
    classes: dict[str, ClassDefinition] = {}
    for snapshot in discover_source_snapshots(sources=sources, repo_root=None):
        indexed: ProjectIndex = build_file_index(snapshot=snapshot)
        functions.update(indexed.functions)
        classes.update(indexed.classes)
    return ProjectIndex(
        functions=functions,
        classes=classes,
        protocol_implementations=_protocol_implementations(classes),
    )


def discover_source_snapshots(
    *, sources: tuple[MappingSource, ...], repo_root: Path | None
) -> tuple[SourceSnapshot, ...]:
    """Discover and read each selected Python source exactly once."""

    snapshots: list[SourceSnapshot] = []
    for path, import_root in _python_files(sources=sources):
        source: bytes = path.read_bytes()
        snapshots.append(
            SourceSnapshot(
                path=path,
                relative_path=_cache_safe_path(path=path, repo_root=repo_root),
                import_root=import_root,
                import_root_identity=_cache_safe_path(path=import_root, repo_root=repo_root),
                module_name=_module_name(path=path, import_root=import_root),
                source=source,
                source_fingerprint=fingerprint_source(source).value,
            )
        )
    return tuple(snapshots)


def build_file_index(*, snapshot: SourceSnapshot) -> ProjectIndex:
    """Extract map declarations from one immutable source snapshot."""

    try:
        artifact: PythonSourceArtifact = parse_python_source(
            path=snapshot.path,
            content=snapshot.source,
            source_fingerprint=snapshot.source_fingerprint,
        )
    except PythonSourceParseError as error:
        raise MapError(f"Could not parse {snapshot.path}: {error.message}") from error
    module: ast.Module = artifact.module
    functions: dict[str, FunctionDefinition] = {}
    classes: dict[str, ClassDefinition] = {}
    imports: ModuleImports = _imports(
        module=module,
        module_name=snapshot.module_name,
        package_module=snapshot.path.name == INIT_MODULE_FILE_NAME,
    )
    for node in module.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            definition: FunctionDefinition = _function_definition(
                node=node,
                module_name=snapshot.module_name,
                path=snapshot.path,
                imports=imports,
            )
            functions[definition.key] = definition
        elif isinstance(node, ast.ClassDef):
            class_definition: ClassDefinition = _class_definition(
                node=node,
                module_name=snapshot.module_name,
                path=snapshot.path,
                imports=imports,
            )
            classes[class_definition.key] = class_definition
            for child in node.body:
                if not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                definition = _function_definition(
                    node=child,
                    module_name=snapshot.module_name,
                    path=snapshot.path,
                    imports=imports,
                    owning_class=node.name,
                )
                functions[definition.key] = definition
    return ProjectIndex(
        functions=functions,
        classes=classes,
        protocol_implementations=_protocol_implementations(classes),
    )


def select_function(
    *, definitions: dict[str, FunctionDefinition], symbol: str
) -> FunctionDefinition:
    """Resolve a bare, dotted, or path-qualified requested function."""

    if PATH_SYMBOL_SEPARATOR in symbol:
        path_fragment, function_name = symbol.rsplit(PATH_SYMBOL_SEPARATOR, maxsplit=1)
        normalized_fragment: str = path_fragment.replace(
            WINDOWS_PATH_SEPARATOR, POSIX_PATH_SEPARATOR
        ).removesuffix(".py")
        matches: tuple[FunctionDefinition, ...] = tuple(
            definition
            for definition in definitions.values()
            if definition.qualified_name == function_name
            and definition.path.as_posix().removesuffix(".py").endswith(normalized_fragment)
        )
    elif symbol in definitions:
        return definitions[symbol]
    elif QUALIFIED_NAME_SEPARATOR in symbol:
        matches = tuple(
            definition for definition in definitions.values() if definition.qualified_name == symbol
        )
    else:
        matches = tuple(
            definition for definition in definitions.values() if definition.name == symbol
        )
    if len(matches) == 1:
        return matches[0]
    if not matches:
        hint: str = (
            f" Use a full dotted key or path::{symbol}."
            if QUALIFIED_NAME_SEPARATOR in symbol
            else ""
        )
        raise MapError(f"Unknown project function: {symbol}.{hint}")
    choices: str = ", ".join(sorted(definition.key for definition in matches))
    raise MapError(
        f"Ambiguous function {symbol}; choose a full dotted key: {choices}; "
        f"or use path::{symbol if QUALIFIED_NAME_SEPARATOR in symbol else 'Class.method'}"
    )


def _function_definition(
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_name: str,
    path: Path,
    imports: ModuleImports,
    owning_class: str | None = None,
) -> FunctionDefinition:
    return FunctionDefinition(
        module_name=module_name,
        name=node.name,
        path=path,
        node=node,
        imports=imports,
        owning_class=owning_class,
    )


def _class_definition(
    *,
    node: ast.ClassDef,
    module_name: str,
    path: Path,
    imports: ModuleImports,
) -> ClassDefinition:
    return ClassDefinition(
        module_name=module_name,
        name=node.name,
        path=path,
        node=node,
        imports=imports,
        bases=tuple(node.bases),
        base_keys=_base_keys(
            bases=tuple(node.bases),
            module_name=module_name,
            imports=imports,
        ),
        protocol=_is_protocol(
            bases=tuple(node.bases),
            imports=imports,
        ),
        class_attributes=_class_attributes(node),
        instance_attributes=_instance_attributes(
            node=node,
            imports=imports,
        ),
    )


def _protocol_implementations(
    classes: dict[str, ClassDefinition],
) -> dict[str, tuple[str, ...]]:
    return ProjectIndex.build_protocol_implementation_keys(
        class_bases={key: definition.base_keys for key, definition in classes.items()},
        protocol_keys=frozenset(key for key, definition in classes.items() if definition.protocol),
    )


def _base_keys(
    *, bases: tuple[ast.expr, ...], module_name: str, imports: ModuleImports
) -> tuple[str, ...]:
    keys: list[str] = []
    for base in bases:
        key: str | None = _base_key(expression=base, module_name=module_name, imports=imports)
        if key is not None:
            keys.append(key)
    return tuple(keys)


def _base_key(*, expression: ast.expr, module_name: str, imports: ModuleImports) -> str | None:
    if isinstance(expression, ast.Subscript):
        return _base_key(expression=expression.value, module_name=module_name, imports=imports)
    if isinstance(expression, ast.Name):
        imported: tuple[str, str] | None = imports.runtime.symbols.get(expression.id)
        if imported is not None:
            return ClassDefinition.build_key(module_name=imported[0], name=imported[1])
        return ClassDefinition.build_key(module_name=module_name, name=expression.id)
    if isinstance(expression, ast.Attribute):
        spelling: str = _expression_name(expression)
        first, separator, remainder = spelling.partition(QUALIFIED_NAME_SEPARATOR)
        imported_module: str | None = imports.runtime.modules.get(first)
        if separator and imported_module is not None:
            return f"{imported_module}.{remainder}"
        return spelling
    return None


def _class_attributes(node: ast.ClassDef) -> dict[str, ClassReference]:
    attributes: dict[str, ClassReference] = {}
    invalid: set[str] = set()
    for statement in node.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            name: str = statement.target.id
            if name not in invalid:
                attributes[name] = ClassReference(statement.annotation, annotation=True)
            continue
        assigned_names: frozenset[str] = _class_assigned_names(statement)
        invalid.update(assigned_names)
        for name in assigned_names:
            attributes.pop(name, None)
    return attributes


def _instance_attributes(
    *,
    node: ast.ClassDef,
    imports: ModuleImports,
) -> dict[str, ClassReference]:
    attributes: dict[str, ClassReference] = _property_attributes(
        node=node,
        imports=imports,
    )
    invalid: set[str] = set()
    for method in node.body:
        if not isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for statement in method.body:
            binding: tuple[str, ClassReference] | None = _self_attribute_binding(statement)
            target_names: frozenset[str] = _self_attribute_targets(statement)
            if binding is None:
                invalid.update(target_names)
                for target_name in target_names:
                    attributes.pop(target_name, None)
                continue
            name, reference = binding
            for target_name in target_names - {name}:
                invalid.add(target_name)
                attributes.pop(target_name, None)
            previous: ClassReference | None = attributes.get(name)
            if name in invalid or (
                previous is not None
                and (
                    previous.annotation != reference.annotation
                    or ast.dump(previous.expression) != ast.dump(reference.expression)
                )
            ):
                invalid.add(name)
                attributes.pop(name, None)
            else:
                attributes[name] = reference
    return attributes


def _property_attributes(
    *,
    node: ast.ClassDef,
    imports: ModuleImports,
) -> dict[str, ClassReference]:
    attributes: dict[str, ClassReference] = {}
    for method in node.body:
        if not isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef) or method.returns is None:
            continue
        if _is_property(
            method=method,
            imports=imports,
        ):
            attributes[method.name] = ClassReference(method.returns, annotation=True)
    return attributes


def _is_property(
    *,
    method: ast.FunctionDef | ast.AsyncFunctionDef,
    imports: ModuleImports,
) -> bool:
    for decorator in method.decorator_list:
        spelling: str = _expression_name(decorator)
        if isinstance(decorator, ast.Name) and decorator.id in imports.runtime.symbols:
            imported: tuple[str, str] = imports.runtime.symbols[decorator.id]
            spelling = f"{imported[0]}.{imported[1]}"
        elif isinstance(decorator, ast.Attribute):
            first, separator, remainder = spelling.partition(".")
            imported_module: str | None = imports.runtime.modules.get(first)
            if separator and imported_module is not None:
                spelling = f"{imported_module}.{remainder}"
        if spelling in PROPERTY_DECORATOR_NAMES:
            return True
    return False


def _self_attribute_binding(statement: ast.stmt) -> tuple[str, ClassReference] | None:
    if isinstance(statement, ast.AnnAssign):
        name: str | None = _self_attribute_name(statement.target)
        if name is not None:
            return name, ClassReference(statement.annotation, annotation=True)
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        name = _self_attribute_name(statement.targets[0])
        if name is not None and isinstance(statement.value, ast.Call):
            return name, ClassReference(statement.value.func, annotation=False)
    return None


def _self_attribute_targets(node: ast.AST) -> frozenset[str]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        return frozenset()
    names: set[str] = set()
    targets: tuple[ast.expr, ...] = ()
    if isinstance(node, ast.AnnAssign | ast.AugAssign):
        targets = (node.target,)
    elif isinstance(node, ast.Assign | ast.Delete):
        targets = tuple(node.targets)
    for target in targets:
        names.update(_self_attribute_names(target))
    for child in ast.iter_child_nodes(node):
        names.update(_self_attribute_targets(child))
    return frozenset(names)


def _self_attribute_names(node: ast.expr) -> set[str]:
    name: str | None = _self_attribute_name(node)
    if name is not None:
        return {name}
    names: set[str] = set()
    if isinstance(node, ast.Tuple | ast.List):
        for element in node.elts:
            names.update(_self_attribute_names(element))
    elif isinstance(node, ast.Starred):
        names.update(_self_attribute_names(node.value))
    return names


def _self_attribute_name(node: ast.expr) -> str | None:
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == SELF_RECEIVER_NAME
    ):
        return node.attr
    return None


def _class_assigned_names(node: ast.AST) -> frozenset[str]:
    if isinstance(node, ast.Lambda):
        return frozenset()
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return frozenset({node.name})
    names: set[str] = set()
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
        names.add(node.id)
    elif isinstance(node, ast.Import | ast.ImportFrom):
        for alias in node.names:
            names.add(alias.asname or alias.name.split(".", maxsplit=1)[0])
    elif isinstance(node, ast.ExceptHandler) and node.name is not None:
        names.add(node.name)
    elif isinstance(node, ast.MatchAs) and node.name is not None:
        names.add(node.name)
    elif isinstance(node, ast.MatchStar) and node.name is not None:
        names.add(node.name)
    elif isinstance(node, ast.MatchMapping) and node.rest is not None:
        names.add(node.rest)
    for child in ast.iter_child_nodes(node):
        names.update(_class_assigned_names(child))
    return frozenset(names)


def _is_protocol(
    *,
    bases: tuple[ast.expr, ...],
    imports: ModuleImports,
) -> bool:
    for base in bases:
        base_expression: ast.expr = base.value if isinstance(base, ast.Subscript) else base
        spelling: str = _expression_name(base_expression)
        if isinstance(base_expression, ast.Name) and base_expression.id in imports.runtime.symbols:
            imported: tuple[str, str] = imports.runtime.symbols[base_expression.id]
            spelling = f"{imported[0]}.{imported[1]}"
        elif isinstance(base_expression, ast.Attribute) and isinstance(
            base_expression.value, ast.Name
        ):
            module: str | None = imports.runtime.modules.get(base_expression.value.id)
            if module is not None:
                spelling = f"{module}.{base_expression.attr}"
        if spelling in PROTOCOL_BASE_NAMES:
            return True
    return False


def _expression_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix: str = _expression_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _python_files(*, sources: tuple[MappingSource, ...]) -> tuple[tuple[Path, Path], ...]:
    discovered: dict[Path, Path] = {}
    for source in sources:
        for path in source.scan_path.rglob("*.py"):
            resolved_path: Path = path.resolve()
            relative_parts: tuple[str, ...] = resolved_path.relative_to(source.scan_path).parts
            if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_parts):
                continue
            discovered.setdefault(resolved_path, source.import_root)
    return tuple((path, discovered[path]) for path in sorted(discovered))


def _module_name(*, path: Path, import_root: Path) -> str:
    parts: tuple[str, ...] = path.relative_to(import_root).parts
    module_parts: tuple[str, ...] = (*parts[:-1], parts[-1].removesuffix(".py"))
    if module_parts[-1] == INIT_MODULE_NAME:
        module_parts = module_parts[:-1]
    return ".".join(module_parts)


def _cache_safe_path(*, path: Path, repo_root: Path | None) -> str:
    if repo_root is not None and path.is_relative_to(repo_root):
        return path.relative_to(repo_root).as_posix()
    return path.as_posix()


def _imports(*, module: ast.Module, module_name: str, package_module: bool) -> ModuleImports:
    return _collect_imports(
        nodes=tuple(module.body),
        module_name=module_name,
        package_module=package_module,
        imports=ModuleImports(
            runtime=ImportView(symbols={}, modules={}),
            annotation=ImportView(symbols={}, modules={}),
        ),
    )


def _collect_imports(
    *,
    nodes: tuple[ast.stmt, ...],
    module_name: str,
    package_module: bool,
    imports: ModuleImports,
) -> ModuleImports:
    runtime: ImportView = imports.runtime
    annotation: ImportView = imports.annotation
    for node in nodes:
        if isinstance(node, ast.Import | ast.ImportFrom):
            runtime = _updated_import_view(
                node=node,
                module_name=module_name,
                package_module=package_module,
                view=runtime,
            )
            annotation = _updated_import_view(
                node=node,
                module_name=module_name,
                package_module=package_module,
                view=annotation,
            )
        elif isinstance(node, ast.If) and _is_type_checking_guard(
            expression=node.test,
            imports=runtime,
        ):
            guarded_imports: tuple[ast.stmt, ...] = tuple(
                child for child in node.body if isinstance(child, ast.Import | ast.ImportFrom)
            )
            annotation = _collect_view_imports(
                nodes=guarded_imports,
                module_name=module_name,
                package_module=package_module,
                view=annotation,
            )
            runtime_imports: tuple[ast.stmt, ...] = tuple(
                child for child in node.orelse if isinstance(child, ast.Import | ast.ImportFrom)
            )
            runtime = _collect_view_imports(
                nodes=runtime_imports,
                module_name=module_name,
                package_module=package_module,
                view=runtime,
            )
    return ModuleImports(runtime=runtime, annotation=annotation)


def _collect_view_imports(
    *,
    nodes: tuple[ast.stmt, ...],
    module_name: str,
    package_module: bool,
    view: ImportView,
) -> ImportView:
    for node in nodes:
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        view = _updated_import_view(
            node=node,
            module_name=module_name,
            package_module=package_module,
            view=view,
        )
    return view


def _updated_import_view(
    *,
    node: ast.Import | ast.ImportFrom,
    module_name: str,
    package_module: bool,
    view: ImportView,
) -> ImportView:
    symbols: dict[str, tuple[str, str]] = dict(view.symbols)
    modules: dict[str, str] = dict(view.modules)
    if isinstance(node, ast.ImportFrom):
        imported_from: str | None = _import_from_module(
            node=node,
            module_name=module_name,
            package_module=package_module,
        )
        if imported_from is None:
            return view
        for alias in node.names:
            local_name: str = alias.asname or alias.name
            symbols[local_name] = (imported_from, alias.name)
            modules[local_name] = f"{imported_from}.{alias.name}"
    else:
        for alias in node.names:
            modules[alias.asname or alias.name.split(".", maxsplit=1)[0]] = alias.name
    return ImportView(symbols=symbols, modules=modules)


def _is_type_checking_guard(
    *,
    expression: ast.expr,
    imports: ImportView,
) -> bool:
    spelling: str = _expression_name(expression)
    if isinstance(expression, ast.Name) and expression.id in imports.symbols:
        imported: tuple[str, str] = imports.symbols[expression.id]
        spelling = f"{imported[0]}.{imported[1]}"
    elif isinstance(expression, ast.Attribute):
        first, separator, remainder = spelling.partition(".")
        imported_module: str | None = imports.modules.get(first)
        if separator and imported_module is not None:
            spelling = f"{imported_module}.{remainder}"
    return spelling in TYPE_CHECKING_NAMES


def _import_from_module(
    *, node: ast.ImportFrom, module_name: str, package_module: bool
) -> str | None:
    if node.level == 0:
        return node.module
    package_parts: list[str] = module_name.split(".")
    if not package_module:
        package_parts = package_parts[:-1]
    parent_count: int = node.level - 1
    if parent_count > len(package_parts):
        return None
    base_parts: list[str] = package_parts[: len(package_parts) - parent_count]
    if node.module is not None:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts) or None
