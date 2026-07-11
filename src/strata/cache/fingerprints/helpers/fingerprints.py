"""Canonical persistent cache fingerprint construction."""

from __future__ import annotations

import hashlib
import inspect
import json
import platform
from collections.abc import Mapping
from importlib.metadata import version
from pathlib import Path

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
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
    """Return a deterministic identity for the complete validated configuration."""

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


def implementation_fingerprint(*, package_root: Path) -> CacheFingerprint:
    """Return a content identity for all Python implementation files."""

    files: list[CanonicalValue] = []
    for path in sorted(package_root.rglob("*.py")):
        files.append(
            [
                path.relative_to(package_root).as_posix(),
                source_fingerprint(path.read_bytes()).value,
            ]
        )
    return canonical_fingerprint(files)


def global_fingerprint(
    *,
    implementation: CacheFingerprint,
    config: CacheFingerprint,
    ruleset: CacheFingerprint,
    strata_version: str | None = None,
) -> CacheFingerprint:
    """Return the complete process-independent global cache identity."""

    payload: CanonicalValue = {
        "config": config.value,
        "implementation": implementation.value,
        "python_version": platform.python_version(),
        "ruleset": ruleset.value,
        "schema_version": CACHE_SCHEMA_VERSION,
        "strata_version": strata_version or version("stratalint"),
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
