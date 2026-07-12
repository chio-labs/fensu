"""Shared helpers for rule authoring tests."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import strata.rules
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext

_BANNED_IMPORT_ROOTS: frozenset[str] = frozenset(
    {
        "asyncio",
        "concurrent",
        "ctypes",
        "datetime",
        "fileinput",
        "ftplib",
        "getpass",
        "glob",
        "http",
        "importlib",
        "inspect",
        "io",
        "linecache",
        "mmap",
        "multiprocessing",
        "os",
        "platform",
        "pkgutil",
        "random",
        "secrets",
        "select",
        "shutil",
        "signal",
        "smtplib",
        "socket",
        "sqlite3",
        "ssl",
        "subprocess",
        "sys",
        "sysconfig",
        "tempfile",
        "threading",
        "time",
        "tokenize",
        "urllib",
        "uuid",
        "zoneinfo",
    }
)
_BANNED_BUILTIN_CALLS: frozenset[str] = frozenset({"__import__", "eval", "exec", "input", "open"})
_BANNED_OPERATION_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "absolute",
        "chmod",
        "cwd",
        "exists",
        "expanduser",
        "glob",
        "hardlink_to",
        "home",
        "is_dir",
        "is_file",
        "is_mount",
        "is_symlink",
        "iterdir",
        "lstat",
        "mkdir",
        "open",
        "owner",
        "read_bytes",
        "read_text",
        "readlink",
        "rename",
        "resolve",
        "rglob",
        "rmdir",
        "samefile",
        "stat",
        "symlink_to",
        "touch",
        "unlink",
        "walk",
        "write_bytes",
        "write_text",
    }
)
_TRACKED_FACADE_ATTRIBUTE: str = "project"


@dataclass(frozen=True)
class HermeticityScan:
    """Complete scan outcome for rule-execution hermeticity."""

    module_count: int
    violations: tuple[str, ...]


def empty_check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """A no-op rule check body usable as a placeholder in tests."""

    return []


def scan_rules_hermeticity(*, excluded_packages: tuple[str, ...]) -> HermeticityScan:
    """Scan installed rule-execution modules for untracked side-effect operations."""

    package_root: Path = Path(strata.rules.__file__).resolve().parent
    module_count: int = 0
    violations: list[str] = []
    for path in sorted(package_root.rglob("*.py")):
        relative: Path = path.relative_to(package_root)
        if relative.parts[0] in excluded_packages:
            continue
        module_count += 1
        tree: ast.Module = ast.parse(path.read_text(encoding="utf-8"))
        violations.extend(_module_violations(tree=tree, module=relative.as_posix()))
    return HermeticityScan(module_count=module_count, violations=tuple(violations))


def _module_violations(*, tree: ast.Module, module: str) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(
                f"{module}:{node.lineno} imports {alias.name}"
                for alias in node.names
                if alias.name.split(".")[0] in _BANNED_IMPORT_ROOTS
            )
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.level == 0 and node.module.split(".")[0] in _BANNED_IMPORT_ROOTS:
                violations.append(f"{module}:{node.lineno} imports from {node.module}")
        if isinstance(node, ast.Call):
            violation: str | None = _call_violation(call=node, module=module)
            if violation is not None:
                violations.append(violation)
    return violations


def _call_violation(*, call: ast.Call, module: str) -> str | None:
    if isinstance(call.func, ast.Name) and call.func.id in _BANNED_BUILTIN_CALLS:
        return f"{module}:{call.lineno} calls builtin {call.func.id}"
    if not isinstance(call.func, ast.Attribute):
        return None
    if call.func.attr not in _BANNED_OPERATION_ATTRIBUTES:
        return None
    if _TRACKED_FACADE_ATTRIBUTE in _receiver_names(call.func.value):
        return None
    return f"{module}:{call.lineno} calls untracked operation {call.func.attr}"


def _receiver_names(receiver: ast.expr) -> tuple[str, ...]:
    names: list[str] = []
    current: ast.expr = receiver
    while isinstance(current, ast.Attribute):
        names.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        names.append(current.id)
    return tuple(names)
