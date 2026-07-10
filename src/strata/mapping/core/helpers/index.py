"""Index project functions and statically resolvable imports."""

from __future__ import annotations

import ast

from strata.config.core.models import Config
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import DiscoveredTree, ScopedFile
from strata.mapping.core.exceptions import MapError
from strata.mapping.core.models import FunctionDefinition


def build_function_index(*, config: Config) -> dict[str, FunctionDefinition]:
    """Build fully-qualified top-level function definitions for configured roots."""

    tree: DiscoveredTree = discover_files(config)
    definitions: dict[str, FunctionDefinition] = {}
    for scoped_file in tree.files:
        if scoped_file.scope != "root":
            continue
        try:
            module: ast.Module = ast.parse(
                scoped_file.path.read_text(encoding="utf-8"), filename=str(scoped_file.path)
            )
        except SyntaxError as error:
            raise MapError(f"Could not parse {scoped_file.path}: {error.msg}") from error
        module_name: str = _module_name(scoped_file=scoped_file)
        imported_symbols, imported_modules = _imports(module)
        for node in module.body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            definition: FunctionDefinition = FunctionDefinition(
                module_name=module_name,
                name=node.name,
                path=scoped_file.path,
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

    if "::" in symbol:
        path_fragment, function_name = symbol.rsplit("::", maxsplit=1)
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


def _module_name(*, scoped_file: ScopedFile) -> str:
    parts: tuple[str, ...] = scoped_file.relative_parts
    module_parts: tuple[str, ...] = (
        scoped_file.root.name,
        *parts[:-1],
        parts[-1].removesuffix(".py"),
    )
    if module_parts[-1] == "__init__":
        module_parts = module_parts[:-1]
    return ".".join(module_parts)


def _imports(module: ast.Module) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    symbols: dict[str, tuple[str, str]] = {}
    modules: dict[str, str] = {}
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            for alias in node.names:
                symbols[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules[alias.asname or alias.name.split(".", maxsplit=1)[0]] = alias.name
    return symbols, modules
