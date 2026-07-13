"""Shared helpers for rule authoring tests."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import singledispatch
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


class _HermeticityVisitor(ast.NodeVisitor):
    def __init__(self, *, module: str) -> None:
        self._module: str = module
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        banned: filter[ast.alias] = filter(
            lambda alias: alias.name.split(".")[0] in _BANNED_IMPORT_ROOTS,
            node.names,
        )
        self.violations.extend(
            f"{self._module}:{node.lineno} imports {alias.name}" for alias in banned
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_name: str = node.module or ""
        forbidden: bool = node.level == 0 and module_name.split(".")[0] in _BANNED_IMPORT_ROOTS
        self.violations.extend(
            {False: (), True: (f"{self._module}:{node.lineno} imports from {module_name}",)}[
                forbidden
            ]
        )

    def visit_Call(self, node: ast.Call) -> None:
        violation: str | None = _call_violation(call=node, module=self._module)
        self.violations.extend(filter(None, (violation,)))
        self.generic_visit(node)


def empty_check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """A no-op rule check body usable as a placeholder in tests."""

    return []


def scan_rules_hermeticity(*, excluded_packages: tuple[str, ...]) -> HermeticityScan:
    """Scan installed rule-execution modules for untracked side-effect operations."""

    package_root: Path = Path(strata.rules.__file__).resolve().parent
    module_count: int = 0
    violations: list[str] = []
    paths: filter[Path] = filter(
        lambda path: path.relative_to(package_root).parts[0] not in excluded_packages,
        sorted(package_root.rglob("*.py")),
    )
    for path in paths:
        relative: Path = path.relative_to(package_root)
        module_count += 1
        tree: ast.Module = ast.parse(path.read_text(encoding="utf-8"))
        violations.extend(_module_violations(tree=tree, module=relative.as_posix()))
    return HermeticityScan(module_count=module_count, violations=tuple(violations))


def _module_violations(*, tree: ast.Module, module: str) -> list[str]:
    visitor: _HermeticityVisitor = _HermeticityVisitor(module=module)
    visitor.visit(tree)
    return visitor.violations


def _call_violation(*, call: ast.Call, module: str) -> str | None:
    return _call_function_violation(call.func, module=module, line=call.lineno)


@singledispatch
def _call_function_violation(node: ast.expr, *, module: str, line: int) -> str | None:
    del node, module, line
    return None


@_call_function_violation.register
def _(node: ast.Name, *, module: str, line: int) -> str | None:
    return {
        False: None,
        True: f"{module}:{line} calls builtin {node.id}",
    }[node.id in _BANNED_BUILTIN_CALLS]


@_call_function_violation.register
def _(node: ast.Attribute, *, module: str, line: int) -> str | None:
    untracked: bool = (
        node.attr in _BANNED_OPERATION_ATTRIBUTES
        and _TRACKED_FACADE_ATTRIBUTE not in _receiver_names(node.value)
    )
    return {
        False: None,
        True: f"{module}:{line} calls untracked operation {node.attr}",
    }[untracked]


def _receiver_names(receiver: ast.expr) -> tuple[str, ...]:
    names: list[str] = []
    current: ast.expr = receiver
    while isinstance(current, ast.Attribute):
        names.append(current.attr)
        current = current.value
    names.append(getattr(current, "id", ""))
    return tuple(filter(None, names))
