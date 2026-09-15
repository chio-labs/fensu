"""Validate and evaluate one native Rust custom-rule host request."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast

from fensu.cli.constants import (
    RUST_CUSTOM_FACT_SCHEMA_VERSION,
    RUST_CUSTOM_HOST_PROTOCOL_VERSION,
    RUST_CUSTOM_PARSER_CONTRACT_VERSION,
)
from fensu.cli.exceptions import CliCommandError
from fensu.config.main.load_target_project_config import load_target_project_config
from fensu.config.main.resolve_target_root import resolve_target_root
from fensu.config.models import LoadedConfig, ResolvedTargetRoot
from fensu.config.types import AnalyzerId
from fensu.evaluation.main.evaluate_rust_custom_rules import evaluate_rust_custom_rules
from fensu.rules.authoring.main.build_rust_project_tree import build_rust_project_tree
from fensu.rules.authoring.main.build_rust_workspace_facts import build_rust_workspace_facts
from fensu.rules.authoring.main.select_rust_workspace_facts import select_rust_workspace_facts
from fensu.rules.authoring.models import (
    ProjectPath,
    ProjectTree,
    RustFileFacts,
    RustWorkspaceFacts,
)
from fensu.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from fensu.rules.catalog.models import RuleSelection


def build_rust_custom_response(*, request: object, runtime_version: str) -> dict[str, object]:
    """Return the successful protocol response for one validated native request."""

    envelope: dict[str, object] = _object(value=request, name="Rust custom host request")
    _fields(
        value=envelope,
        expected={"protocol", "runtime_version", "payload"},
        name="request",
    )
    protocol: int = _integer(value=envelope["protocol"], name="protocol")
    requested_runtime: str = _string(value=envelope["runtime_version"], name="runtime version")
    if protocol != RUST_CUSTOM_HOST_PROTOCOL_VERSION:
        raise CliCommandError(
            f"Unsupported Rust custom-host protocol {protocol}; "
            f"expected {RUST_CUSTOM_HOST_PROTOCOL_VERSION}."
        )
    if requested_runtime != runtime_version:
        raise CliCommandError(
            f"Rust custom-host runtime {runtime_version} does not match {requested_runtime}."
        )
    payload: dict[str, object] = _object(value=envelope["payload"], name="Rust custom host payload")
    _fields(
        value=payload,
        expected={"target", "show_warnings", "cache_enabled", "facts", "subjects"},
        name="Rust custom host payload",
    )
    target_value: object = payload["target"]
    target: str | None = (
        None if target_value is None else _string(value=target_value, name="target")
    )
    show_warnings: bool = _boolean(value=payload["show_warnings"], name="show_warnings")
    cache_enabled: bool = _boolean(value=payload["cache_enabled"], name="cache_enabled")
    workspace: RustWorkspaceFacts = build_rust_workspace_facts(payload=payload["facts"])
    if workspace.schema_version != RUST_CUSTOM_FACT_SCHEMA_VERSION:
        raise CliCommandError(
            f"Unsupported Rust fact schema {workspace.schema_version}; "
            f"expected {RUST_CUSTOM_FACT_SCHEMA_VERSION}."
        )
    if workspace.parser_contract != RUST_CUSTOM_PARSER_CONTRACT_VERSION:
        raise CliCommandError(
            f"Unsupported Rust parser contract {workspace.parser_contract}; "
            f"expected {RUST_CUSTOM_PARSER_CONTRACT_VERSION}."
        )
    loaded: LoadedConfig = load_target_project_config(start=Path.cwd(), target=target)
    if loaded.config.analyzer is not AnalyzerId.RUST:
        raise CliCommandError("Rust custom host requires a Rust analyzer target.")
    loaded = replace(
        loaded,
        config=replace(
            loaded.config,
            cache=replace(loaded.config.cache, enabled=cache_enabled),
        ),
    )
    repository_root: Path = loaded.source.path.parent.resolve()
    resolved: ResolvedTargetRoot = resolve_target_root(
        config=loaded.config, repo_root=repository_root
    )
    tree: ProjectTree
    selected_files: Mapping[ProjectPath, RustFileFacts]
    tree, selected_files = build_rust_project_tree(
        subjects=payload["subjects"], workspace=workspace
    )
    workspace = select_rust_workspace_facts(workspace=workspace, files=selected_files)
    selection: RuleSelection = build_check_rule_selection(
        config=loaded.config,
        repo_root=repository_root,
        project_root=resolved.path,
        include_warnings=show_warnings,
        catalogue=loaded.catalogue,
    )
    findings: list[dict[str, object]]
    dependencies: list[dict[str, str]]
    blocking_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    cacheable: bool
    findings, dependencies, blocking_codes, warning_codes, cacheable = evaluate_rust_custom_rules(
        root=resolved.path,
        tree=tree,
        workspace=workspace,
        config=loaded.config,
        selection=selection,
        include_warnings=show_warnings,
    )
    return {
        "protocol": protocol,
        "runtime_version": runtime_version,
        "error": None,
        "payload": {
            "findings": findings,
            "blocking_codes": list(blocking_codes),
            "warning_codes": list(warning_codes),
            "dependencies": dependencies,
            "cacheable": cacheable,
        },
        "messages": [],
    }


def _object(*, value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise CliCommandError(f"{name} must be an object.")
    return cast("dict[str, object]", value)


def _fields(*, value: dict[str, object], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise CliCommandError(f"{name} fields do not match the supported protocol.")


def _string(*, value: object, name: str) -> str:
    if not isinstance(value, str):
        raise CliCommandError(f"{name} must be a string.")
    return value


def _integer(*, value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CliCommandError(f"{name} must be an integer.")
    return value


def _boolean(*, value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise CliCommandError(f"{name} must be a boolean.")
    return value
