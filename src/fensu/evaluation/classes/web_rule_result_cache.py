"""Persistent per-subject cache for hosted web custom-rule results."""

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
from fensu.evaluation.classes.web_dependency_observer import WebDependencyObserver
from fensu.evaluation.constants import (
    WEB_CUSTOM_CACHE_RECORD_FIELDS,
    WEB_CUSTOM_CACHE_RELATIVE_PATH,
    WEB_CUSTOM_CACHE_SCHEMA,
    WEB_CUSTOM_DEPENDENCY_FIELDS,
    WEB_CUSTOM_FINDING_FIELDS,
    WEB_CUSTOM_FINDING_SEVERITIES,
    WEB_DEPENDENCY_FILE,
    WEB_DEPENDENCY_FILES,
    WEB_DEPENDENCY_TREE_CHILDREN,
    WEB_DEPENDENCY_TREE_DESCENDANTS,
    WEB_DEPENDENCY_TREE_FILES,
    WEB_DEPENDENCY_TREE_FILES_UNDER,
    WEB_DEPENDENCY_TREE_GLOB,
    WEB_DEPENDENCY_TREE_PATHS,
    WEB_DEPENDENCY_TREE_POSITION,
    WEB_GRAPH_CYCLES,
    WEB_GRAPH_DEPENDENCIES,
    WEB_GRAPH_DEPENDENTS,
    WEB_GRAPH_IMPORTS,
    WEB_GRAPH_NODE,
    WEB_GRAPH_NODES,
)
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    ProjectPath,
    ProjectTree,
    RuleSpec,
    WebWorkspaceFacts,
)


class WebRuleResultCache:
    """Replay observed tree/fact answers before reusing one rule subject."""

    def __init__(
        self,
        *,
        root: Path,
        config: Config,
        fact_schema: str,
        parser_contract: str,
        enabled: bool,
    ) -> None:
        self._path: Path = root / WEB_CUSTOM_CACHE_RELATIVE_PATH
        self._config: Config = config
        custom_rules: CacheFingerprint | None = build_custom_rules_fingerprint(
            config=config, repo_root=root
        )
        self._custom_rules_identity: str = "" if custom_rules is None else custom_rules.value
        self._fact_schema: str = fact_schema
        self._parser_contract: str = parser_contract
        self._runtime_version: str = version("fensu")
        self._enabled: bool = enabled and custom_rules is not None
        self._loaded: dict[str, dict[str, object]] = self._read_records()
        self._current: dict[str, dict[str, object]] = {}

    def read(
        self,
        *,
        rule: RuleSpec,
        subject_kind: str,
        subject_identity: str,
        tree: ProjectTree,
        graph: ArchitectureGraph,
        workspace: WebWorkspaceFacts,
    ) -> tuple[list[dict[str, object]], list[dict[str, str]]] | None:
        """Return one reusable subject result only while all observed answers match."""

        if not self._enabled:
            return None
        key: str = self._key(
            rule=rule, subject_kind=subject_kind, subject_identity=subject_identity
        )
        record: dict[str, object] | None = self._loaded.get(key)
        if record is None or set(record) != WEB_CUSTOM_CACHE_RECORD_FIELDS:
            return None
        dependencies: list[dict[str, str]] | None = _dependencies(record["dependencies"])
        findings: list[dict[str, object]] | None = _findings(record["findings"])
        if dependencies is None or findings is None:
            return None
        for dependency in dependencies:
            try:
                current: str | None = _replayed_answer(
                    dependency=dependency, tree=tree, graph=graph, workspace=workspace
                )
            except (TypeError, ValueError):
                return None
            if current != dependency["answer"]:
                return None
        self._current[key] = record
        return findings, dependencies

    def write(
        self,
        *,
        rule: RuleSpec,
        subject_kind: str,
        subject_identity: str,
        findings: list[dict[str, object]],
        dependencies: list[dict[str, str]],
    ) -> None:
        """Stage one freshly evaluated subject result for atomic publication."""

        if not self._enabled:
            return
        key: str = self._key(
            rule=rule, subject_kind=subject_kind, subject_identity=subject_identity
        )
        self._current[key] = {
            "dependencies": dependencies,
            "findings": findings,
        }

    def publish(self) -> None:
        """Atomically replace the cache generation with current evaluated subjects."""

        if not self._enabled:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path = self._path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(
                json.dumps(
                    {"records": self._current, "schema": WEB_CUSTOM_CACHE_SCHEMA},
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            temporary.replace(self._path)
        except OSError:
            return

    def _key(self, *, rule: RuleSpec, subject_kind: str, subject_identity: str) -> str:
        return build_rule_subject_fingerprint(
            config=self._config,
            custom_rules_identity=self._custom_rules_identity,
            fact_schema=self._fact_schema,
            parser_contract=self._parser_contract,
            runtime_version=self._runtime_version,
            rule=rule,
            subject_kind=subject_kind,
            subject_identity=subject_identity,
        )

    def _read_records(self) -> dict[str, dict[str, object]]:
        if not self._enabled:
            return {}
        try:
            payload: object = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict) or payload.get("schema") != WEB_CUSTOM_CACHE_SCHEMA:
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


def _replayed_answer(
    *,
    dependency: dict[str, str],
    tree: ProjectTree,
    graph: ArchitectureGraph,
    workspace: WebWorkspaceFacts,
) -> str | None:
    observations: list[dict[str, str]] = []
    observer: WebDependencyObserver = WebDependencyObserver(
        requester=dependency["requester"], observations=observations
    )
    observed_tree: ProjectTree = tree.observed(observer)
    observed_workspace: WebWorkspaceFacts = workspace.observed(observer)
    observed_graph: ArchitectureGraph = graph.observed(observer)
    kind: str = dependency["kind"]
    query: str = dependency["query"]
    if kind == WEB_DEPENDENCY_TREE_PATHS:
        _ = observed_tree.paths
    elif kind == WEB_DEPENDENCY_TREE_FILES:
        _ = observed_tree.files
    elif kind == WEB_DEPENDENCY_TREE_CHILDREN:
        _ = observed_tree.children(query)
    elif kind == WEB_DEPENDENCY_TREE_DESCENDANTS:
        _ = observed_tree.descendants(query)
    elif kind == WEB_DEPENDENCY_TREE_GLOB:
        pattern: str = dependency["answer"].partition("\0")[0]
        _ = observed_tree.glob(pattern)
    elif kind == WEB_DEPENDENCY_TREE_FILES_UNDER:
        _ = observed_tree.files_under(query)
    elif kind == WEB_DEPENDENCY_TREE_POSITION:
        _ = observed_tree.position(ProjectPath(query))
    elif kind == WEB_DEPENDENCY_FILES:
        _ = observed_workspace.files
    elif kind == WEB_DEPENDENCY_FILE:
        _ = observed_workspace.file(ProjectPath(query))
    elif kind == WEB_GRAPH_NODES:
        _ = observed_graph.nodes
    elif kind == WEB_GRAPH_NODE:
        _ = observed_graph.node(ProjectPath(query))
    elif kind == WEB_GRAPH_IMPORTS:
        _ = observed_graph.imports(ProjectPath(query))
    elif kind == WEB_GRAPH_DEPENDENCIES:
        _ = observed_graph.dependencies(ProjectPath(query))
    elif kind == WEB_GRAPH_DEPENDENTS:
        _ = observed_graph.dependents(ProjectPath(query))
    elif kind == WEB_GRAPH_CYCLES:
        _ = observed_graph.cycles()
    else:
        return None
    return observations[0]["answer"] if len(observations) == 1 else None


def _dependencies(value: object) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    dependencies: list[dict[str, str]] = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != WEB_CUSTOM_DEPENDENCY_FIELDS
            or any(not isinstance(entry, str) for entry in item.values())
        ):
            return None
        dependencies.append(cast("dict[str, str]", item))
    return dependencies


def _findings(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    findings: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != WEB_CUSTOM_FINDING_FIELDS:
            return None
        finding: dict[str, object] = cast("dict[str, object]", item)
        code: object = finding["code"]
        path: object = finding["path"]
        line: object = finding["line"]
        column: object = finding["column"]
        symbol: object = finding["symbol"]
        message: object = finding["message"]
        remediation: object = finding["remediation"]
        severity: object = finding["severity"]
        if (
            not isinstance(code, str)
            or not isinstance(path, str)
            or not _optional_position(line)
            or not _optional_position(column)
            or symbol is not None
            and not isinstance(symbol, str)
            or not isinstance(message, str)
            or remediation is not None
            and not isinstance(remediation, str)
            or not isinstance(severity, str)
            or severity not in WEB_CUSTOM_FINDING_SEVERITIES
        ):
            return None
        findings.append(finding)
    return findings


def _optional_position(value: object) -> bool:
    return value is None or isinstance(value, int) and not isinstance(value, bool) and value >= 0
