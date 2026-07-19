"""Helpers for persistent cache fingerprint tests."""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path
from types import MappingProxyType

import pytest

import strata.cache.fingerprints.main.build_global as build_global_module
from strata.config.constants import DEFAULT_THRESHOLDS
from strata.config.models import Config
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import (
    ExecutionOwner,
    Family,
    RuleContext,
    RuleKind,
    Threshold,
)


def _leave_package_available(*, monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    del monkeypatch, root


def _disable_package(*, monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    del root
    monkeypatch.setattr(build_global_module, "_loaded_package_root", lambda: None)


def _install_sourceless_package(*, monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    root.mkdir()
    monkeypatch.setattr(build_global_module, "_loaded_package_root", lambda: root)


def _install_incomplete_package(*, monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    bytecode: Path = root / "__pycache__/missing.cpython-312.pyc"
    bytecode.parent.mkdir()
    bytecode.write_bytes(b"orphan bytecode")
    monkeypatch.setattr(build_global_module, "_loaded_package_root", lambda: root)


def config_with_statement_threshold(*, value: int, reverse_mapping_order: bool) -> Config:
    """Return a config whose threshold mapping has the requested insertion order."""

    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds[Threshold.MAX_STATEMENTS] = value
    items: list[tuple[Threshold, int]] = list(thresholds.items())
    reverse: Callable[[], None] = {
        False: lambda: None,
        True: items.reverse,
    }[reverse_mapping_order]
    reverse()
    return Config(
        roots=("src/pkg",),
        thresholds=MappingProxyType(dict(items)),
    )


def write_implementation(*, root: Path, source: str) -> None:
    """Write one implementation file below a package root."""

    path: Path = root / "domain/helpers.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def rule_with_message(
    message: str,
    *,
    execution_owner: ExecutionOwner = ExecutionOwner.FILE,
) -> RuleSpec:
    """Return one deterministic fake rule for ruleset fingerprint tests."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module, ctx
        return []

    return RuleSpec(
        code="XCA001",
        family=Family.CUSTOM,
        slug="cache-test",
        message=message,
        check=check,
        execution_owner=execution_owner,
    )


def write_custom_rule(*, path: Path, returns_fault: bool) -> None:
    """Write one custom rule with stable metadata and selectable behavior."""

    result: str = {False: "[]", True: "[ctx.path_fault()]"}[returns_fault]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "from __future__ import annotations\n\n"
        "import ast\n\n"
        "from strata import Family, Fault, RuleContext, rule\n\n"
        "@rule(code='XCF001', family=Family.CUSTOM, slug='cache-source', message='stable')\n"
        "def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    del module\n"
        f"    return {result}\n",
        encoding="utf-8",
    )


def configure_package_availability(
    *,
    monkeypatch: pytest.MonkeyPatch,
    available: bool,
    source_available: bool,
    complete_source: bool,
    empty_package_root: Path,
) -> None:
    """Disable loaded-package discovery for conservative fallback coverage."""

    configure: Callable[..., None] = {
        (False, False, False): _disable_package,
        (True, False, False): _install_sourceless_package,
        (True, True, False): _install_incomplete_package,
        (True, True, True): _leave_package_available,
    }[(available, source_available, complete_source)]
    configure(monkeypatch=monkeypatch, root=empty_package_root)


def custom_fingerprint_rule(*, code: str, cacheable: bool) -> RuleSpec:
    """Return one custom rule spec with an explicit cacheability declaration."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module, ctx
        return []

    return RuleSpec(
        code=code,
        family=Family.CUSTOM,
        slug="fingerprint-custom",
        message="fingerprint custom",
        check=check,
        kind=RuleKind.CUSTOM,
        cacheable=cacheable,
    )
