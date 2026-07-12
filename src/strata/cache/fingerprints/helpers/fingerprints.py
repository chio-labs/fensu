"""Canonical persistent cache fingerprint construction."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import platform
from collections.abc import Mapping
from importlib.machinery import ModuleSpec
from importlib.metadata import version
from pathlib import Path

from strata.cache.fingerprints.constants import (
    BYTECODE_SUFFIX,
    EVALUATION_FINGERPRINT_CONTRACT_VERSION,
    NATIVE_MODULE_SUFFIXES,
    PACKAGE_INIT_FILE_NAME,
    PYTHON_CACHE_DIRECTORY_NAME,
    PYTHON_SOURCE_SUFFIX,
)
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results.models import CachedFileResult, DependencyObservation
from strata.cache.storage.constants import CACHE_SCHEMA_VERSION
from strata.config.core.models import Config, RuleExceptionEntry
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleCheck, Threshold


def canonical_fingerprint(value: CanonicalValue) -> CacheFingerprint:
    """Return a SHA-256 identity for one canonical JSON value."""

    encoded: bytes = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return source_fingerprint(encoded)


def source_fingerprint(source: bytes) -> CacheFingerprint:
    """Return a SHA-256 identity for complete source bytes."""

    return CacheFingerprint(value=hashlib.sha256(source).hexdigest())


def config_fingerprint(config: Config) -> CacheFingerprint:
    """Return a deterministic identity for semantic evaluation configuration."""

    payload: CanonicalValue = {
        "contracts": dict(sorted(config.contracts.items())),
        "ignore": list(config.ignore),
        "role_thresholds": _role_threshold_values(config.role_thresholds),
        "roots": list(config.roots),
        "rule_exceptions": [_rule_exception_value(item) for item in config.rule_exceptions],
        "rule_modules": list(config.rule_modules),
        "rule_paths": list(config.rule_paths),
        "select": list(config.select),
        "tests": list(config.tests),
        "thresholds": _threshold_values(config.thresholds),
        "tooling": list(config.tooling),
    }
    return canonical_fingerprint(payload)


def ruleset_fingerprint(ruleset: tuple[RuleSpec, ...]) -> CacheFingerprint:
    """Return a deterministic identity for the effective ordered ruleset."""

    payload: CanonicalValue = [
        {
            "cacheable": rule.cacheable,
            "check_module": rule.check.__module__,
            "check_name": _check_name(rule.check),
            "code": rule.code,
            "enabled_by_default": rule.enabled_by_default,
            "family": rule.family.value,
            "kind": rule.kind.value,
            "message": rule.message,
            "remediation": rule.remediation,
            "severity": rule.severity.value,
            "slug": rule.slug,
            "source": rule.source,
            "source_fingerprint": _check_source_fingerprint(rule.check),
        }
        for rule in ruleset
    ]
    return canonical_fingerprint(payload)


def custom_rules_fingerprint(*, config: Config, repo_root: Path) -> CacheFingerprint | None:
    """Return a content identity for every configured custom-rule file or None."""

    files: list[CanonicalValue] = []
    for rule_path in sorted(config.rule_paths):
        configured: Path = Path(rule_path)
        resolved: Path = (
            configured.resolve() if configured.is_absolute() else (repo_root / configured).resolve()
        )
        entries: tuple[Path, ...] | None = _rule_source_files(resolved)
        if entries is None:
            return None
        files.extend(_fingerprinted_file(path=path, label=rule_path) for path in entries)
    for module_name in sorted(config.rule_modules):
        module_root: Path | None = _rule_module_location(module_name, repo_root=repo_root)
        entries = None if module_root is None else _rule_source_files(module_root)
        if entries is None:
            return None
        files.extend(_fingerprinted_file(path=path, label=module_name) for path in entries)
    return canonical_fingerprint(files)


def _fingerprinted_file(*, path: Path, label: str) -> CanonicalValue:
    return [label, path.name, source_fingerprint(path.read_bytes()).value]


def _rule_source_files(location: Path) -> tuple[Path, ...] | None:
    if location.is_file():
        return (location,)
    if location.is_dir():
        return tuple(sorted(location.rglob(f"*{PYTHON_SOURCE_SUFFIX}")))
    return None


def _rule_module_location(module_name: str, *, repo_root: Path) -> Path | None:
    module_parts: tuple[str, ...] = tuple(module_name.split("."))
    candidate: Path = repo_root.joinpath(*module_parts)
    if candidate.is_dir() and (candidate / "__init__.py").is_file():
        return candidate
    module_file: Path = candidate.with_suffix(PYTHON_SOURCE_SUFFIX)
    if module_file.is_file():
        return module_file
    return _installed_module_location(module_name)


def _installed_module_location(module_name: str) -> Path | None:
    try:
        spec: ModuleSpec | None = importlib.util.find_spec(module_name)
    except (ImportError, ValueError):
        return None
    if spec is None or spec.origin is None:
        return None
    origin: Path = Path(spec.origin)
    if not origin.is_file():
        return None
    return origin.parent if origin.name == PACKAGE_INIT_FILE_NAME else origin


def implementation_fingerprint(*, package_root: Path) -> CacheFingerprint:
    """Return a content identity for all Python implementation files."""

    files: list[CanonicalValue] = []
    for path in _implementation_paths(package_root):
        files.append(
            [
                path.relative_to(package_root).as_posix(),
                source_fingerprint(path.read_bytes()).value,
            ]
        )
    return canonical_fingerprint(files)


def implementation_identity_is_complete(*, package_root: Path) -> bool:
    """Return whether the loaded package exposes fingerprintable implementation files."""

    return bool(_implementation_paths(package_root))


def global_fingerprint(
    *,
    implementation: CacheFingerprint,
    config: CacheFingerprint,
    ruleset: CacheFingerprint,
    custom_rules: CacheFingerprint,
    strata_version: str | None = None,
) -> CacheFingerprint:
    """Return the complete process-independent global cache identity."""

    payload: CanonicalValue = {
        "config": config.value,
        "custom_rules": custom_rules.value,
        "evaluation_contract_version": EVALUATION_FINGERPRINT_CONTRACT_VERSION,
        "implementation": implementation.value,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "ruleset": ruleset.value,
        "schema_version": CACHE_SCHEMA_VERSION,
        "strata_version": strata_version or version("stratalint"),
    }
    return canonical_fingerprint(payload)


def file_result_fingerprint(
    *,
    global_fingerprint: CacheFingerprint,
    result: CachedFileResult,
) -> CacheFingerprint:
    """Return the correctness identity for one reusable file result."""

    payload: CanonicalValue = {
        "dependencies": [_dependency_observation_value(item) for item in result.dependencies],
        "global_fingerprint": global_fingerprint.value,
        "path": result.path,
        "source_fingerprint": result.source_fingerprint.value,
    }
    return canonical_fingerprint(payload)


def file_result_record_fingerprint(result: CachedFileResult) -> CacheFingerprint:
    """Return the integrity identity for every persisted file-result value."""

    payload: CanonicalValue = {
        "applied_exception_keys": [
            {"path": item.path, "rule": item.rule, "symbol": item.symbol}
            for item in result.applied_exception_keys
        ],
        "dependencies": [_dependency_observation_value(item) for item in result.dependencies],
        "faults": [
            {
                "code": item.code,
                "column": item.column,
                "line": item.line,
                "message": item.message,
                "path": item.path,
                "remediation": item.remediation,
            }
            for item in result.faults
        ],
        "path": result.path,
        "source_fingerprint": result.source_fingerprint.value,
    }
    return canonical_fingerprint(payload)


def _rule_exception_value(item: RuleExceptionEntry) -> CanonicalValue:
    return {
        "path": item.path,
        "reason": item.reason,
        "rule": item.rule,
        "symbols": list(item.symbols),
    }


def _dependency_observation_value(item: DependencyObservation) -> CanonicalValue:
    answer: CanonicalValue
    if isinstance(item.answer, tuple):
        answer = list(item.answer)
    else:
        answer = item.answer
    return {
        "answer": answer,
        "dependency_path": item.dependency_path,
        "kind": item.kind.value,
        "pattern": item.pattern,
        "query_path": item.query_path,
        "recursive": item.recursive,
        "requester_path": item.requester_path,
    }


def _threshold_values(thresholds: Mapping[Threshold, int]) -> dict[str, CanonicalValue]:
    values: dict[str, CanonicalValue] = {}
    for threshold, value in sorted(thresholds.items(), key=lambda item: item[0].value):
        values[threshold.value] = value
    return values


def _role_threshold_values(
    role_thresholds: Mapping[str, Mapping[Threshold, int]],
) -> dict[str, CanonicalValue]:
    values: dict[str, CanonicalValue] = {}
    for role, thresholds in sorted(role_thresholds.items()):
        values[role] = _threshold_values(thresholds)
    return values


def _check_name(check: RuleCheck) -> str:
    name: object = getattr(check, "__qualname__", None)
    return name if isinstance(name, str) else type(check).__qualname__


def _check_source_fingerprint(check: RuleCheck) -> CanonicalValue:
    try:
        source_path: str | None = inspect.getsourcefile(check)
    except TypeError:
        return None
    if source_path is None:
        return None
    path: Path = Path(source_path)
    if not path.is_file():
        return None
    return source_fingerprint(path.read_bytes()).value


def _bytecode_source_path(bytecode_path: Path) -> Path:
    if bytecode_path.parent.name == PYTHON_CACHE_DIRECTORY_NAME:
        source_name: str = bytecode_path.name.split(".", maxsplit=1)[0]
        return bytecode_path.parent.parent / f"{source_name}{PYTHON_SOURCE_SUFFIX}"
    return bytecode_path.with_suffix(PYTHON_SOURCE_SUFFIX)


def _implementation_paths(package_root: Path) -> tuple[Path, ...]:
    paths: set[Path] = set(package_root.rglob(f"*{PYTHON_SOURCE_SUFFIX}"))
    for bytecode_path in package_root.rglob(f"*{BYTECODE_SUFFIX}"):
        if not _bytecode_source_path(bytecode_path).is_file():
            paths.add(bytecode_path)
    for suffix in NATIVE_MODULE_SUFFIXES:
        paths.update(package_root.rglob(f"*{suffix}"))
    return tuple(sorted(paths))
