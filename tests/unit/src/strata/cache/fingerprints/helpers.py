"""Helpers for persistent cache fingerprint tests."""

from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

import pytest

import strata.cache.fingerprints.main.build_global as build_global_module
from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.models import CachedFault, CachedFileResult, DependencyObservation
from strata.config.core.constants import DEFAULT_THRESHOLDS
from strata.config.core.models import Config
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, RuleKind, Threshold


def config_with_statement_threshold(*, value: int, reverse_mapping_order: bool) -> Config:
    """Return a config whose threshold mapping has the requested insertion order."""

    thresholds: dict[Threshold, int] = dict(DEFAULT_THRESHOLDS)
    thresholds[Threshold.MAX_STATEMENTS] = value
    items: list[tuple[Threshold, int]] = list(thresholds.items())
    if reverse_mapping_order:
        items.reverse()
    return Config(
        roots=("src/pkg",),
        thresholds=MappingProxyType(dict(items)),
    )


def write_implementation(*, root: Path, source: str) -> None:
    """Write one implementation file below a package root."""

    path: Path = root / "domain/helpers.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def rule_with_message(message: str) -> RuleSpec:
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
    )


def write_custom_rule(*, path: Path, returns_fault: bool) -> None:
    """Write one custom rule with stable metadata and selectable behavior."""

    result: str = "[ctx.path_fault()]" if returns_fault else "[]"
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


def cached_file_result(*, dependency_answer: bool, fault_message: str) -> CachedFileResult:
    """Return one deterministic file result for fingerprint tests."""

    return CachedFileResult(
        path="src/pkg/models.py",
        source_fingerprint=CacheFingerprint("a" * 64),
        faults=(
            CachedFault(
                code="SFA001",
                path="src/pkg/models.py",
                message=fault_message,
                line=1,
                column=0,
            ),
        ),
        applied_exception_keys=(),
        dependencies=(
            DependencyObservation(
                requester_path="src/pkg/models.py",
                query_path="src/pkg/dependency.py",
                dependency_path="src/pkg/dependency.py",
                kind=ProjectDependencyKind.EXISTS,
                answer=dependency_answer,
            ),
        ),
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

    if not available:
        monkeypatch.setattr(build_global_module, "_loaded_package_root", lambda: None)
    elif not source_available:
        empty_package_root.mkdir()
        monkeypatch.setattr(
            build_global_module,
            "_loaded_package_root",
            lambda: empty_package_root,
        )
    elif not complete_source:
        empty_package_root.mkdir()
        (empty_package_root / "__init__.py").write_text("", encoding="utf-8")
        bytecode: Path = empty_package_root / "__pycache__/missing.cpython-312.pyc"
        bytecode.parent.mkdir()
        bytecode.write_bytes(b"orphan bytecode")
        monkeypatch.setattr(
            build_global_module,
            "_loaded_package_root",
            lambda: empty_package_root,
        )


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
