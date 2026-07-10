"""Index project functions and statically resolvable imports."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.mapping.core.constants import (
    EXCLUDED_DIRECTORY_NAMES,
    INIT_MODULE_FILE_NAME,
    INIT_MODULE_NAME,
    PATH_SYMBOL_SEPARATOR,
)
from strata.mapping.core.exceptions import MapError
from strata.mapping.core.models import FunctionDefinition, MappingSource


def build_function_index(*, sources: tuple[MappingSource, ...]) -> dict[str, FunctionDefinition]:
    """Build fully-qualified top-level functions from project mapping sources."""

    definitions: dict[str, FunctionDefinition] = {}
    for path, import_root in _python_files(sources=sources):
        try:
            module: ast.Module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            raise MapError(f"Could not parse {path}: {error.msg}") from error
        module_name: str = _module_name(path=path, import_root=import_root)
        imported_symbols, imported_modules = _imports(
            module=module,
            module_name=module_name,
            package_module=path.name == INIT_MODULE_FILE_NAME,
        )
        for node in module.body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            definition: FunctionDefinition = FunctionDefinition(
                module_name=module_name,
                name=node.name,
                path=path,
                node=node,
                imported_symbols=imported_symbols,
                imported_modules=imported_modules,
            )
            definitions[f"{module_name}.{node.name}"] = definition
    return definitions


def select_function(
    *, definitions: dict[str, FunctionDefinition], symbol: str
) -> FunctionDefinition:
    """Resolve a bare, dotted, or path-qualified requested function."""

    if PATH_SYMBOL_SEPARATOR in symbol:
        path_fragment, function_name = symbol.rsplit(PATH_SYMBOL_SEPARATOR, maxsplit=1)
        matches: tuple[FunctionDefinition, ...] = tuple(
            definition
            for definition in definitions.values()
            if definition.name == function_name
            and str(definition.path).removesuffix(".py").endswith(path_fragment.removesuffix(".py"))
        )
    elif symbol in definitions:
        return definitions[symbol]
    else:
        matches = tuple(
            definition for definition in definitions.values() if definition.name == symbol
        )
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise MapError(f"Unknown project function: {symbol}")
    choices: str = ", ".join(
        sorted(f"{definition.module_name}.{definition.name}" for definition in matches)
    )
    raise MapError(f"Ambiguous function {symbol}; choose one of: {choices}")


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


def _imports(
    *, module: ast.Module, module_name: str, package_module: bool
) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    symbols: dict[str, tuple[str, str]] = {}
    modules: dict[str, str] = {}
    for node in module.body:
        if isinstance(node, ast.ImportFrom):
            imported_from: str | None = _import_from_module(
                node=node,
                module_name=module_name,
                package_module=package_module,
            )
            if imported_from is None:
                continue
            for alias in node.names:
                local_name: str = alias.asname or alias.name
                symbols[local_name] = (imported_from, alias.name)
                modules[local_name] = f"{imported_from}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules[alias.asname or alias.name.split(".", maxsplit=1)[0]] = alias.name
    return symbols, modules


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
