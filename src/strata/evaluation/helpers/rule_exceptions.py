"""Validate and apply centralized symbol-scoped rule exceptions."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.config.exceptions import ConfigError
from strata.config.models import Config, RuleExceptionEntry
from strata.evaluation.models import ParsedModule, RuleExceptionKey
from strata.rules.authoring.models import Fault


def validate_exception_targets(*, config: Config, repo_root: Path) -> None:
    """Validate configured paths and qualified symbols against repository source."""

    for exception in config.rule_exceptions:
        path: Path = repo_root / exception.path
        _validate_exception_path(path=path, repo_root=repo_root, configured=exception.path)
        module: ast.Module = _parse_exception_path(path)
        symbols: tuple[str, ...] = _defined_function_symbols(module)
        duplicate_symbols: frozenset[str] = frozenset(
            symbol for symbol in symbols if symbols.count(symbol) > 1
        )
        for symbol in exception.symbols:
            if symbol in duplicate_symbols:
                raise ConfigError(
                    f"Rule exception symbol is ambiguous in {exception.path}: {symbol}."
                )
            if symbol not in symbols:
                raise ConfigError(
                    f"Rule exception symbol does not exist in {exception.path}: {symbol}."
                )


def configured_exception_keys(config: Config) -> frozenset[RuleExceptionKey]:
    """Return every configured rule/path/symbol exception as an exact key."""

    keys: set[RuleExceptionKey] = set()
    for exception in config.rule_exceptions:
        for symbol in exception.symbols:
            keys.add(RuleExceptionKey(rule=exception.rule, path=exception.path, symbol=symbol))
    return frozenset(keys)


def suppress_faults(
    *,
    faults: list[Fault],
    parsed_module: ParsedModule,
    config: Config,
    repo_root: Path,
) -> tuple[list[Fault], frozenset[RuleExceptionKey]]:
    """Suppress exact matching faults and return the applied exception keys."""

    relative_path: str = parsed_module.scoped_file.path.relative_to(repo_root).as_posix()
    exceptions: tuple[RuleExceptionEntry, ...] = tuple(
        exception for exception in config.rule_exceptions if exception.path == relative_path
    )
    if not exceptions or not faults:
        return faults, frozenset()
    retained: list[Fault] = []
    applied: set[RuleExceptionKey] = set()
    for fault in faults:
        owner: str | None = _fault_owner(fault=fault, parsed_module=parsed_module)
        matching: RuleExceptionEntry | None = next(
            (
                exception
                for exception in exceptions
                if exception.rule == fault.code and owner in exception.symbols
            ),
            None,
        )
        if matching is None or owner is None:
            retained.append(fault)
            continue
        applied.add(RuleExceptionKey(rule=fault.code, path=relative_path, symbol=owner))
    return retained, frozenset(applied)


def stale_exception_error(
    *, configured: frozenset[RuleExceptionKey], applied: frozenset[RuleExceptionKey]
) -> ConfigError | None:
    """Return an actionable error when any configured exception suppressed no fault."""

    stale: tuple[RuleExceptionKey, ...] = tuple(
        sorted(configured - applied, key=lambda key: (key.rule, key.path, key.symbol))
    )
    if not stale:
        return None
    details: str = ", ".join(f"{key.rule} {key.path}::{key.symbol}" for key in stale)
    return ConfigError(f"Stale rule exception(s) suppressed no faults; remove them: {details}.")


def _validate_exception_path(*, path: Path, repo_root: Path, configured: str) -> None:
    resolved_root: Path = repo_root.resolve()
    resolved_path: Path = path.resolve()
    if not resolved_path.is_relative_to(resolved_root) or not path.is_file():
        raise ConfigError(f"Rule exception path does not exist: {configured}.")


def _parse_exception_path(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        raise ConfigError(f"Could not inspect rule exception path {path}: {error}") from error


def _defined_function_symbols(module: ast.Module) -> tuple[str, ...]:
    return _collect_function_symbols(body=module.body, owner=None)


def _collect_function_symbols(*, body: list[ast.stmt], owner: str | None) -> tuple[str, ...]:
    symbols: list[str] = []
    for node in body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbol: str = node.name if owner is None else f"{owner}.{node.name}"
            symbols.append(symbol)
            symbols.extend(_collect_function_symbols(body=node.body, owner=symbol))
        elif isinstance(node, ast.ClassDef):
            class_owner: str = node.name if owner is None else f"{owner}.{node.name}"
            symbols.extend(_collect_function_symbols(body=node.body, owner=class_owner))
        else:
            nested_statements: list[ast.stmt] = []
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.stmt):
                    nested_statements.append(child)
            symbols.extend(_collect_function_symbols(body=nested_statements, owner=owner))
    return tuple(symbols)


def _fault_owner(*, fault: Fault, parsed_module: ParsedModule) -> str | None:
    if fault.line is None:
        return None
    position: tuple[int, int] = (fault.line, fault.column or 0)
    candidates: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node_type in (ast.FunctionDef, ast.AsyncFunctionDef):
        for node in parsed_module.node_index.get(node_type, ()):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _contains_position(
                node=node, position=position
            ):
                candidates.append(node)
    if not candidates:
        return None
    owner_node: ast.FunctionDef | ast.AsyncFunctionDef = max(
        candidates,
        key=lambda node: _symbol_depth(node=node, parsed_module=parsed_module),
    )
    return _qualified_symbol(node=owner_node, parsed_module=parsed_module)


def _contains_position(
    *, node: ast.FunctionDef | ast.AsyncFunctionDef, position: tuple[int, int]
) -> bool:
    start: tuple[int, int] = (node.lineno, node.col_offset)
    end: tuple[int, int] = (node.end_lineno or node.lineno, node.end_col_offset or node.col_offset)
    return start <= position < end


def _symbol_depth(
    *, node: ast.FunctionDef | ast.AsyncFunctionDef, parsed_module: ParsedModule
) -> int:
    return len(_qualified_symbol(node=node, parsed_module=parsed_module).split("."))


def _qualified_symbol(
    *, node: ast.FunctionDef | ast.AsyncFunctionDef, parsed_module: ParsedModule
) -> str:
    parts: list[str] = [node.name]
    current: ast.AST | None = parsed_module.parent_by_node.get(node)
    while current is not None:
        if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            parts.append(current.name)
        current = parsed_module.parent_by_node.get(current)
    return ".".join(reversed(parts))
