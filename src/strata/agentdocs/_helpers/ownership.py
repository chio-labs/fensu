"""Build and parse deterministic generated-skill ownership metadata."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import cast

from strata.agentdocs.constants import (
    GENERATED_MARKER,
    OWNERSHIP_MARKER_PREFIX,
    OWNERSHIP_MARKER_SCHEMA,
    SKILL_INPUT_FINGERPRINT_SCHEMA,
)
from strata.agentdocs.models import SkillGenerationContext, SkillOwnership
from strata.config.models import Config, RuleExceptionEntry, ThresholdOverride
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Threshold


def owned_skill_content(*, context: SkillGenerationContext, content: str) -> str:
    """Embed ownership and deterministic input/content identities after the legacy marker."""

    owner: str = skill_owner_key(context)
    input_fingerprint: str = skill_input_fingerprint(context)
    provisional: dict[str, object] = {
        "schema": OWNERSHIP_MARKER_SCHEMA,
        "identity": context.identity,
        "owner": owner,
        "input_fingerprint": input_fingerprint,
        "content_fingerprint": "",
    }
    provisional_marker: str = _ownership_marker(provisional)
    provisional_content: str = content.replace(
        GENERATED_MARKER, f"{GENERATED_MARKER}\n{provisional_marker}", 1
    )
    content_fingerprint: str = hashlib.sha256(provisional_content.encode("utf-8")).hexdigest()
    ownership: dict[str, object] = {**provisional, "content_fingerprint": content_fingerprint}
    return provisional_content.replace(provisional_marker, _ownership_marker(ownership), 1)


def skill_input_fingerprint(context: SkillGenerationContext) -> str:
    """Return a renderer-free identity for every semantic skill-generation input."""

    payload: dict[str, object] = {
        "schema": SKILL_INPUT_FINGERPRINT_SCHEMA,
        "config_source": {
            "kind": context.config_source.kind.value,
            "path": context.config_source.path.resolve().as_posix(),
        },
        "project_root": context.project_root.resolve().as_posix(),
        "install_root": context.install_root.resolve().as_posix(),
        "git_root": None if context.git_root is None else context.git_root.resolve().as_posix(),
        "project_prefix": context.project_prefix,
        "identity": context.identity,
        "config": _config_value(context.config),
        "catalogue": [_rule_value(rule) for rule in sorted(context.catalogue, key=_rule_key)],
        "blocking": [_rule_value(rule) for rule in sorted(context.blocking_rules, key=_rule_key)],
        "warnings": [_rule_value(rule) for rule in sorted(context.warning_rules, key=_rule_key)],
        "ignored": [_rule_value(rule) for rule in sorted(context.ignored_rules, key=_rule_key)],
    }
    encoded: bytes = json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def skill_content_fingerprint_matches(*, content: bytes, ownership: SkillOwnership) -> bool:
    """Return whether installed bytes match their embedded content identity."""

    final_marker: bytes = _ownership_marker(_ownership_value(ownership)).encode("ascii")
    if content.splitlines().count(final_marker) != 1:
        return False
    provisional_value: dict[str, object] = {
        **_ownership_value(ownership),
        "content_fingerprint": "",
    }
    provisional: bytes = content.replace(
        final_marker,
        _ownership_marker(provisional_value).encode("ascii"),
        1,
    )
    return hashlib.sha256(provisional).hexdigest() == ownership.content_fingerprint


def skill_owner_key(context: SkillGenerationContext) -> str:
    """Return the stable local owner key for one authoritative config source."""

    source: bytes = context.config_source.path.resolve().as_posix().encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def parse_skill_ownership(content: bytes) -> SkillOwnership | None:
    """Parse one exact structured marker, returning None for legacy or malformed data."""

    prefix: bytes = OWNERSHIP_MARKER_PREFIX.encode("ascii")
    suffix: bytes = b" -->"
    matching: list[bytes] = [line for line in content.splitlines() if line.startswith(prefix)]
    if len(matching) != 1 or not matching[0].endswith(suffix):
        return None
    try:
        value: object = json.loads(matching[0][len(prefix) : -len(suffix)])
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    typed_value: dict[str, object] = cast("dict[str, object]", value)
    fields: tuple[str, ...] = (
        "schema",
        "identity",
        "owner",
        "input_fingerprint",
        "content_fingerprint",
    )
    if set(typed_value) != set(fields):
        return None
    schema: object = typed_value["schema"]
    identity: object = typed_value["identity"]
    owner: object = typed_value["owner"]
    input_fingerprint: object = typed_value["input_fingerprint"]
    content_fingerprint: object = typed_value["content_fingerprint"]
    string_values: tuple[object, ...] = (
        identity,
        owner,
        input_fingerprint,
        content_fingerprint,
    )
    if schema != OWNERSHIP_MARKER_SCHEMA or not all(
        isinstance(item, str) for item in string_values
    ):
        return None
    return SkillOwnership(
        schema=cast("int", schema),
        identity=cast("str", identity),
        owner=cast("str", owner),
        input_fingerprint=cast("str", input_fingerprint),
        content_fingerprint=cast("str", content_fingerprint),
    )


def generated_marker_present(content: bytes) -> bool:
    """Return whether content contains the exact legacy generated-marker line."""

    return GENERATED_MARKER.encode("ascii") in content.splitlines()


def _ownership_marker(value: dict[str, object]) -> str:
    return (
        OWNERSHIP_MARKER_PREFIX
        + json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + " -->"
    )


def _ownership_value(ownership: SkillOwnership) -> dict[str, object]:
    return {
        "schema": ownership.schema,
        "identity": ownership.identity,
        "owner": ownership.owner,
        "input_fingerprint": ownership.input_fingerprint,
        "content_fingerprint": ownership.content_fingerprint,
    }


def _config_value(config: Config) -> dict[str, object]:
    return {
        "roots": list(config.roots),
        "tests": list(config.tests),
        "tooling": list(config.tooling),
        "select": list(config.select),
        "warn": list(config.warn),
        "ignore": list(config.ignore),
        "rule_paths": list(config.rule_paths),
        "rule_modules": list(config.rule_modules),
        "rule_exceptions": [_rule_exception_value(item) for item in config.rule_exceptions],
        "cache": {
            "enabled": config.cache.enabled,
            "require_cacheable": config.cache.require_cacheable,
        },
        "evaluation": {
            "include": list(config.evaluation.include),
            "exclude": list(config.evaluation.exclude),
        },
        "skills": {"name": config.skills.name},
        "thresholds": _threshold_values(config.thresholds),
        "role_thresholds": {
            role: _threshold_values(values)
            for role, values in sorted(config.role_thresholds.items())
        },
        "threshold_overrides": [
            _threshold_override_value(item) for item in config.threshold_overrides
        ],
        "contracts": dict(sorted(config.contracts.items())),
    }


def _rule_value(rule: RuleSpec) -> dict[str, object]:
    return {
        "code": rule.code,
        "family": rule.family.value,
        "slug": rule.slug,
        "message": rule.message,
        "remediation": rule.remediation,
        "severity": rule.severity.value,
        "kind": rule.kind.value,
        "source": rule.source,
        "enabled_by_default": rule.enabled_by_default,
        "cacheable": bool(rule.cacheable),
        "execution_owner": rule.execution_owner.value,
    }


def _rule_key(rule: RuleSpec) -> tuple[str, str]:
    return rule.code, rule.slug


def _threshold_values(values: Mapping[Threshold, int]) -> dict[str, int]:
    return {threshold.value: value for threshold, value in sorted(values.items())}


def _rule_exception_value(item: RuleExceptionEntry) -> dict[str, object]:
    return {
        "rule": item.rule,
        "path": item.path,
        "reason": item.reason,
        "symbols": list(item.symbols),
    }


def _threshold_override_value(item: ThresholdOverride) -> dict[str, object]:
    return {
        "paths": list(item.paths),
        "thresholds": _threshold_values(item.thresholds),
        "reason": item.reason,
    }
