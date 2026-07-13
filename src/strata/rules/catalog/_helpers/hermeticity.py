"""Verify declared-cacheable custom rules against the hermetic import contract."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from strata.config.exceptions import ConfigError
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleKind
from strata.rules.catalog.constants import (
    CACHEABLE_ALLOWED_IMPORT_ROOTS,
    CACHEABLE_BANNED_BUILTIN_CALLS,
    CACHEABLE_UNTRACKED_OPERATION_ATTRIBUTES,
    STRATA_PACKAGE_NAME,
    TRACKED_FACADE_ATTRIBUTE,
)


def validate_cacheable_rules(
    *,
    rules: tuple[RuleSpec, ...],
    allowed_packages: frozenset[str],
) -> None:
    """Reject cacheable custom rules whose source escapes the hermetic contract."""

    scanned: set[Path] = set()
    for rule in rules:
        if rule.kind is not RuleKind.CUSTOM or not rule.cacheable:
            continue
        path: Path | None = _check_source_path(rule)
        if path is None:
            raise ConfigError(
                f"Cacheable rule {rule.code} has no inspectable source file; "
                "remove cacheable=True or define the rule in a plain Python file."
            )
        if path in scanned:
            continue
        scanned.add(path)
        _validate_rule_source(
            rule=rule,
            path=path,
            allowed_packages=allowed_packages,
        )


def _validate_rule_source(
    *,
    rule: RuleSpec,
    path: Path,
    allowed_packages: frozenset[str],
) -> None:
    tree: ast.Module = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Call)):
            continue
        violation: str | None = _node_violation(
            node=node,
            allowed_packages=allowed_packages,
        )
        if violation is not None:
            raise ConfigError(
                f"Cacheable rule {rule.code} ({path}:{node.lineno}) {violation}. "
                "Cacheable rules may only import the standard library allowlist, "
                "strata, and configured rule packages, and must read project "
                "state through ctx.project."
            )


def _node_violation(
    *,
    node: ast.Import | ast.ImportFrom | ast.Call,
    allowed_packages: frozenset[str],
) -> str | None:
    if isinstance(node, ast.Import):
        return _import_violation(names=node.names, allowed_packages=allowed_packages)
    if isinstance(node, ast.ImportFrom):
        if node.level > 0:
            return None
        if node.module is None:
            return "uses an unsupported import form"
        return _module_violation(module=node.module, allowed_packages=allowed_packages)
    return _call_violation(call=node)


def _import_violation(
    *,
    names: list[ast.alias],
    allowed_packages: frozenset[str],
) -> str | None:
    for alias in names:
        violation: str | None = _module_violation(
            module=alias.name,
            allowed_packages=allowed_packages,
        )
        if violation is not None:
            return violation
    return None


def _module_violation(*, module: str, allowed_packages: frozenset[str]) -> str | None:
    root: str = module.partition(".")[0]
    if (
        root in CACHEABLE_ALLOWED_IMPORT_ROOTS
        or root == STRATA_PACKAGE_NAME
        or root in allowed_packages
    ):
        return None
    return f"imports {module}"


def _call_violation(*, call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name) and call.func.id in CACHEABLE_BANNED_BUILTIN_CALLS:
        return f"calls builtin {call.func.id}"
    if not isinstance(call.func, ast.Attribute):
        return None
    if call.func.attr not in CACHEABLE_UNTRACKED_OPERATION_ATTRIBUTES:
        return None
    if TRACKED_FACADE_ATTRIBUTE in _receiver_names(call.func.value):
        return None
    return f"calls untracked operation {call.func.attr}"


def _receiver_names(receiver: ast.expr) -> tuple[str, ...]:
    names: list[str] = []
    current: ast.expr = receiver
    while isinstance(current, ast.Attribute):
        names.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        names.append(current.id)
    return tuple(names)


def _check_source_path(rule: RuleSpec) -> Path | None:
    try:
        source_path: str | None = inspect.getsourcefile(rule.check)
    except TypeError:
        return None
    if source_path is None:
        return None
    path: Path = Path(source_path)
    return path if path.is_file() else None
