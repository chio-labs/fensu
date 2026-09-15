"""Persistent query-observed cache for repository-subject custom rules."""

from __future__ import annotations

import json
import os
from importlib.metadata import version
from pathlib import Path
from typing import cast

from fensu.cache.fingerprints.main.build_custom_rules import build_custom_rules_fingerprint
from fensu.cache.fingerprints.main.build_rule_subject import build_rule_subject_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.config.models import Config
from fensu.evaluation.classes.repository_rule_target import RepositoryRuleTargetView
from fensu.evaluation.classes.repository_rule_targets import RepositoryRuleTargets
from fensu.evaluation.constants import (
    REPOSITORY_CACHE_RECORD_FIELDS,
    REPOSITORY_CUSTOM_CACHE_RELATIVE_PATH,
    REPOSITORY_CUSTOM_CACHE_SCHEMA,
    REPOSITORY_DEPENDENCY_FIELDS,
    REPOSITORY_FACT_SCHEMA_VERSION,
    REPOSITORY_FINDING_FIELDS,
    REPOSITORY_FINDING_SEVERITIES,
    REPOSITORY_RULE_CACHE_CONTRACT_VERSION,
    REPOSITORY_RULE_REQUESTER,
)
from fensu.rules.authoring.models import RuleSpec


class RepositoryRuleResultCache:
    """Replay target-qualified query answers before reusing one repository rule."""

    def __init__(
        self,
        *,
        root: Path,
        config: Config,
        registry_identity: str,
        enabled: bool,
    ) -> None:
        self._root = root.resolve()
        self._config = config
        self._registry_identity = registry_identity
        self._enabled = enabled
        self._path = self._root / REPOSITORY_CUSTOM_CACHE_RELATIVE_PATH
        custom: CacheFingerprint | None = build_custom_rules_fingerprint(
            config=config, repo_root=self._root
        )
        self._custom_identity = "" if custom is None else custom.value
        self._enabled = enabled and custom is not None
        self._records = self._read_records()
        self._stats: dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "writes": 0,
            "non_cacheable": 0,
        }

    @property
    def stats(self) -> dict[str, int]:
        """Return cache counters for normal aggregate CLI reporting."""

        return dict(self._stats)

    def read(
        self, *, rule: RuleSpec, targets: RepositoryRuleTargets
    ) -> tuple[list[dict[str, object]], list[dict[str, str]]] | None:
        """Return a cached result only while every observed target answer matches."""

        if rule.cacheable is not True:
            self._stats["non_cacheable"] += 1
            return None
        if not self._enabled:
            return None
        record: dict[str, object] | None = self._records.get(self._key(rule=rule))
        if record is None:
            self._stats["misses"] += 1
            return None
        if set(record) != REPOSITORY_CACHE_RECORD_FIELDS:
            return self._invalidated()
        findings: list[dict[str, object]] | None = _findings(record["findings"])
        typed_dependencies: list[dict[str, str]] | None = _dependencies(record["dependencies"])
        if findings is None or typed_dependencies is None:
            return self._invalidated()
        for dependency in typed_dependencies:
            target: RepositoryRuleTargetView | None = targets.named(dependency["target"])
            if target is None:
                return self._invalidated()
            try:
                current: str | None = target.replay(
                    kind=dependency["kind"],
                    query=dependency["query"],
                    answer=dependency["answer"],
                )
            except (RuntimeError, TypeError, ValueError):
                return self._invalidated()
            if current != dependency["answer"]:
                return self._invalidated()
        self._stats["hits"] += 1
        return findings, typed_dependencies

    def write(
        self,
        *,
        rule: RuleSpec,
        findings: list[dict[str, object]],
        dependencies: list[dict[str, str]],
    ) -> None:
        """Persist one cacheable repository-rule result atomically."""

        if not self._enabled or rule.cacheable is not True:
            return
        self._records[self._key(rule=rule)] = {
            "findings": findings,
            "dependencies": dependencies,
        }
        self._stats["writes"] += 1
        payload: str = json.dumps(
            {"schema": REPOSITORY_CUSTOM_CACHE_SCHEMA, "records": self._records},
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path = self._path.with_suffix(f"{self._path.suffix}.{os.getpid()}.tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(self._path)
        except OSError:
            return

    def _key(self, *, rule: RuleSpec) -> str:
        return build_rule_subject_fingerprint(
            config=self._config,
            custom_rules_identity=self._custom_identity,
            fact_schema=REPOSITORY_FACT_SCHEMA_VERSION,
            parser_contract=(
                f"{REPOSITORY_RULE_CACHE_CONTRACT_VERSION}\0{self._registry_identity}"
            ),
            runtime_version=version("fensu"),
            rule=rule,
            subject_kind="repository",
            subject_identity=".",
        )

    def _read_records(self) -> dict[str, dict[str, object]]:
        if not self._enabled:
            return {}
        try:
            payload: object = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict) or payload.get("schema") != REPOSITORY_CUSTOM_CACHE_SCHEMA:
            return {}
        records: object = payload.get("records")
        if not isinstance(records, dict):
            return {}
        if any(
            not isinstance(key, str) or not isinstance(value, dict)
            for key, value in records.items()
        ):
            return {}
        return cast("dict[str, dict[str, object]]", records)

    def _invalidated(self) -> None:
        self._stats["invalidations"] += 1
        return None


def _dependencies(value: object) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    dependencies: list[dict[str, str]] = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != REPOSITORY_DEPENDENCY_FIELDS
            or any(not isinstance(entry, str) for entry in item.values())
            or item.get("requester") != REPOSITORY_RULE_REQUESTER
        ):
            return None
        dependencies.append(cast("dict[str, str]", item))
    return dependencies


def _findings(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    findings: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != REPOSITORY_FINDING_FIELDS:
            return None
        finding: dict[str, object] = cast("dict[str, object]", item)
        if (
            not isinstance(finding["code"], str)
            or not isinstance(finding["path"], str)
            or not _optional_position(finding["line"])
            or not _optional_position(finding["column"])
            or finding["symbol"] is not None
            or not isinstance(finding["message"], str)
            or finding["remediation"] is not None
            and not isinstance(finding["remediation"], str)
            or finding["severity"] not in REPOSITORY_FINDING_SEVERITIES
        ):
            return None
        findings.append(finding)
    return findings


def _optional_position(value: object) -> bool:
    return value is None or isinstance(value, int) and not isinstance(value, bool) and value >= 0
