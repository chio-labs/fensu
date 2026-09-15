"""Validate and evaluate one cross-target repository-rule host request."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

from fensu.cli.constants import REPOSITORY_CUSTOM_HOST_PROTOCOL_VERSION
from fensu.cli.exceptions import CliCommandError
from fensu.config.main.load_repository_rule_config import load_repository_rule_config
from fensu.config.models import LoadedConfig
from fensu.evaluation.classes.repository_rule_target import (
    RepositoryRuleTargetView,
    build_repository_rule_target,
)
from fensu.evaluation.constants import MINIMUM_REPOSITORY_TARGETS
from fensu.evaluation.main.evaluate_repository_custom_rules import (
    evaluate_repository_custom_rules,
)
from fensu.rules.catalog.main.build_repository_rule_selection import (
    build_repository_rule_selection,
)
from fensu.rules.catalog.models import RuleSelection


def build_repository_custom_response(*, request: object, runtime_version: str) -> dict[str, object]:
    """Return one successful versioned repository-rule protocol response."""

    envelope: dict[str, object] = _object(value=request, name="Repository custom request")
    _fields(value=envelope, expected={"protocol", "runtime_version", "payload"}, name="request")
    protocol: int = _integer(value=envelope["protocol"], name="protocol")
    if protocol != REPOSITORY_CUSTOM_HOST_PROTOCOL_VERSION:
        raise CliCommandError(f"Unsupported repository custom host protocol: {protocol}.")
    requested_runtime: str = _string(value=envelope["runtime_version"], name="runtime_version")
    if requested_runtime != runtime_version:
        raise CliCommandError(
            f"Repository custom host runtime mismatch: {requested_runtime} != {runtime_version}."
        )
    payload: dict[str, object] = _object(
        value=envelope["payload"], name="Repository custom payload"
    )
    _fields(
        value=payload,
        expected={"show_warnings", "cache_enabled", "targets"},
        name="payload",
    )
    show_warnings: bool = _boolean(value=payload["show_warnings"], name="show_warnings")
    cache_enabled: bool = _boolean(value=payload["cache_enabled"], name="cache_enabled")
    target_payloads: list[object] = _sequence(value=payload["targets"], name="targets")
    if len(target_payloads) < MINIMUM_REPOSITORY_TARGETS:
        raise CliCommandError("Repository rules require at least two named analyzer targets.")
    targets: tuple[RepositoryRuleTargetView, ...] = tuple(
        build_repository_rule_target(payload=item) for item in target_payloads
    )
    names: tuple[str, ...] = tuple(target.identity.name for target in targets)
    if len(names) != len(set(names)) or names != tuple(sorted(names)):
        raise CliCommandError("Repository target identities must be unique and sorted.")
    loaded: LoadedConfig | None = load_repository_rule_config(start=Path.cwd())
    if loaded is None:
        raise CliCommandError("Repository custom host requires repository_rules configuration.")
    repository_root: Path = loaded.source.path.parent.resolve()
    loaded = replace(
        loaded,
        config=replace(
            loaded.config,
            cache=replace(
                loaded.config.cache,
                enabled=loaded.config.cache.enabled and cache_enabled,
            ),
        ),
    )
    selection: RuleSelection = build_repository_rule_selection(
        loaded=loaded,
        target_analyzers=frozenset(target.identity.analyzer for target in targets),
        repo_root=repository_root,
    )
    findings: list[dict[str, object]]
    dependencies: list[dict[str, str]]
    blocking_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    cacheable: bool
    applied_exceptions: int
    cache: dict[str, int]
    (
        findings,
        dependencies,
        blocking_codes,
        warning_codes,
        cacheable,
        applied_exceptions,
        cache,
    ) = evaluate_repository_custom_rules(
        root=repository_root,
        targets=targets,
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
            "applied_exceptions": applied_exceptions,
            "cache": cache,
        },
        "messages": [],
    }


def _object(*, value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise CliCommandError(f"{name} must be an object.")
    return cast("dict[str, object]", value)


def _sequence(*, value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise CliCommandError(f"{name} must be an array.")
    return cast("list[object]", value)


def _fields(*, value: dict[str, object], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise CliCommandError(f"Repository custom {name} contains incompatible fields.")


def _string(*, value: object, name: str) -> str:
    if not isinstance(value, str):
        raise CliCommandError(f"Repository custom {name} must be a string.")
    return value


def _integer(*, value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CliCommandError(f"Repository custom {name} must be an integer.")
    return value


def _boolean(*, value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise CliCommandError(f"Repository custom {name} must be a boolean.")
    return value
