"""Canonical persistent cache fingerprint construction."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
import platform
from collections.abc import Mapping
from importlib.machinery import ModuleSpec
from importlib.metadata import (
    Distribution,
    PackageNotFoundError,
    PackagePath,
    distribution,
    version,
)
from pathlib import Path

from strata.analysis.main.hash_repository_files import hash_repository_files
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
from strata.cache.storage.constants import CACHE_SCHEMA_VERSION
from strata.config.models import Config, RuleExceptionEntry
from strata.instrumentation.constants import CANONICAL_ENCODE_OPERATION, OPERATION_COUNTERS
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleCheck, Threshold

_PACKAGE_RECORD_PREFIX: str = "strata/"
_PACKAGE_RECORD_INIT: str = "strata/__init__.py"


def canonical_fingerprint(value: CanonicalValue) -> CacheFingerprint:
    """Return a SHA-256 identity for one canonical JSON value."""

    OPERATION_COUNTERS.record(operation=CANONICAL_ENCODE_OPERATION)
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
        "evaluation": {
            "exclude": list(config.evaluation.exclude),
            "include": list(config.evaluation.include),
        },
        "ignore": list(config.ignore),
        "role_thresholds": _role_threshold_values(config.role_thresholds),
        "roots": list(config.roots),
        "rule_exceptions": [_rule_exception_value(item) for item in config.rule_exceptions],
        "rule_modules": list(config.rule_modules),
        "rule_paths": list(config.rule_paths),
        "select": list(config.select),
        "skills": {"name": config.skills.name},
        "tests": list(config.tests),
        "threshold_overrides": [
            {
                "paths": list(item.paths),
                "reason": item.reason,
                "thresholds": _threshold_values(item.thresholds),
            }
            for item in config.threshold_overrides
        ],
        "thresholds": _threshold_values(config.thresholds),
        "tooling": list(config.tooling),
        "warn": list(config.warn),
    }
    return canonical_fingerprint(payload)


def ruleset_fingerprint(ruleset: tuple[RuleSpec, ...]) -> CacheFingerprint:
    """Return a deterministic identity for the effective ordered ruleset."""

    source_fingerprints: dict[Path, CanonicalValue] = {}
    payload: CanonicalValue = [
        {
            "cacheable": bool(rule.cacheable),
            "check_module": rule.check.__module__,
            "check_name": _check_name(rule.check),
            "code": rule.code,
            "enabled_by_default": rule.enabled_by_default,
            "execution_owner": rule.execution_owner.value,
            "family": rule.family.value,
            "kind": rule.kind.value,
            "message": rule.message,
            "remediation": rule.remediation,
            "severity": rule.severity.value,
            "slug": rule.slug,
            "source": rule.source,
            "source_fingerprint": _check_source_fingerprint(
                check=rule.check,
                source_fingerprints=source_fingerprints,
            ),
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
        module_root: Path | None = _rule_module_location(
            module_name=module_name, repo_root=repo_root
        )
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


def _rule_module_location(*, module_name: str, repo_root: Path) -> Path | None:
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


def collect_implementation_paths(*, package_root: Path) -> tuple[Path, ...]:
    """Return the complete deterministic implementation path set."""

    return _implementation_paths(package_root)


def installed_implementation_fingerprint(*, package_root: Path) -> CacheFingerprint | None:
    """Return the persisted wheel RECORD identity for the loaded immutable package."""

    try:
        installed: Distribution = distribution("stratalint")
        files: tuple[PackagePath, ...] = tuple(installed.files or ())
        package_files: tuple[PackagePath, ...] = tuple(
            path for path in files if str(path).startswith(_PACKAGE_RECORD_PREFIX)
        )
        package_init: PackagePath | None = next(
            (path for path in package_files if str(path) == _PACKAGE_RECORD_INIT),
            None,
        )
        if (
            package_init is None
            or any(path.hash is None for path in package_files)
            or Path(package_init.locate()).resolve() != (package_root / "__init__.py").resolve()
        ):
            return None
        record: str | None = installed.read_text("RECORD")
        if record is None:
            return None
        return canonical_fingerprint([package_root.resolve().as_posix(), record])
    except (OSError, PackageNotFoundError, RuntimeError, ValueError):
        return None


def implementation_fingerprint(
    *,
    package_root: Path,
    paths: tuple[Path, ...] | None = None,
) -> CacheFingerprint:
    """Return a content identity for all Python implementation files."""

    files: list[CanonicalValue] = []
    implementation_paths: tuple[Path, ...] = (
        paths if paths is not None else collect_implementation_paths(package_root=package_root)
    )
    native_hashes: tuple[str | None, ...] = hash_repository_files(paths=implementation_paths)
    for path, native_hash in zip(implementation_paths, native_hashes, strict=True):
        digest: str = (
            native_hash if native_hash is not None else source_fingerprint(path.read_bytes()).value
        )
        files.append(
            [
                path.relative_to(package_root).as_posix(),
                digest,
            ]
        )
    return canonical_fingerprint(files)


def global_fingerprint(
    *,
    implementation: CacheFingerprint,
    config: CacheFingerprint,
    ruleset: CacheFingerprint,
    custom_rules: CacheFingerprint,
    native_backend_version: str,
    warnings_enabled: bool = False,
    strata_version: str | None = None,
) -> CacheFingerprint:
    """Return the complete process-independent global cache identity."""

    payload: CanonicalValue = {
        "config": config.value,
        "custom_rules": custom_rules.value,
        "evaluation_contract_version": EVALUATION_FINGERPRINT_CONTRACT_VERSION,
        "native_backend_version": native_backend_version,
        "implementation": implementation.value,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "ruleset": ruleset.value,
        "schema_version": CACHE_SCHEMA_VERSION,
        "strata_version": strata_version or version("stratalint"),
        "warnings_enabled": warnings_enabled,
    }
    return canonical_fingerprint(payload)


def _rule_exception_value(item: RuleExceptionEntry) -> CanonicalValue:
    return {
        "path": item.path,
        "reason": item.reason,
        "rule": item.rule,
        "symbols": list(item.symbols),
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


def _check_source_fingerprint(
    *,
    check: RuleCheck,
    source_fingerprints: dict[Path, CanonicalValue],
) -> CanonicalValue:
    try:
        source_path: str | None = inspect.getsourcefile(check)
    except TypeError:
        return None
    if source_path is None:
        return None
    path: Path = Path(source_path)
    if not path.is_file():
        return None
    if path not in source_fingerprints:
        source_fingerprints[path] = _source_path_fingerprint(path)
    return source_fingerprints[path]


def _source_path_fingerprint(path: Path) -> str:
    return source_fingerprint(path.read_bytes()).value


def _bytecode_source_path(bytecode_path: Path) -> Path:
    if bytecode_path.parent.name == PYTHON_CACHE_DIRECTORY_NAME:
        source_name: str = bytecode_path.name.split(".", maxsplit=1)[0]
        return bytecode_path.parent.parent / f"{source_name}{PYTHON_SOURCE_SUFFIX}"
    return bytecode_path.with_suffix(PYTHON_SOURCE_SUFFIX)


def _implementation_paths(package_root: Path) -> tuple[Path, ...]:
    paths: set[Path] = set()
    for directory, directory_names, file_names in os.walk(package_root):
        root: Path = Path(directory)
        for name in (*directory_names, *file_names):
            path: Path = root / name
            if name.endswith(PYTHON_SOURCE_SUFFIX):
                paths.add(path)
            elif name.endswith(BYTECODE_SUFFIX) and not _bytecode_source_path(path).is_file():
                paths.add(path)
            elif name.endswith(NATIVE_MODULE_SUFFIXES):
                paths.add(path)
    return tuple(sorted(paths))
