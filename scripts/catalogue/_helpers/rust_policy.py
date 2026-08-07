"""Render fixed RuleSpec constraints as native Rust constants."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from fensu.cli.constants import SKILLS_METADATA_PROTOCOL_VERSION
from fensu.config.constants import (
    CONFIG_ROLE_NAMES,
    CONTRACT_BEHAVIORS,
    DEFAULT_CACHE_ENABLED,
    DEFAULT_CACHE_REQUIRE_CACHEABLE,
    DEFAULT_CONTRACTS,
    DEFAULT_EXPERIMENTAL_MEMORY,
    DEFAULT_IGNORE,
    DEFAULT_MEMORY_TASKS_ARCHIVE_AFTER_DAYS,
    DEFAULT_SELECT,
    DEFAULT_TEST_PATHS,
    DEFAULT_TEST_SCOPES,
    DEFAULT_THRESHOLDS,
    DEFAULT_WARN,
    RULE_CONFIGURATION_INPUTS,
)
from fensu.rules.authoring.models import RuleConstraint, RuleLimit, RuleSpec


def serialized_native_policy(*, rules: Sequence[RuleSpec]) -> bytes:
    """Return deterministic Rust source for every fixed core constraint."""

    owners: tuple[str, ...] = tuple(rule.code for rule in rules if rule.constraints or rule.limits)
    lines: list[str] = [
        "//! Generated fixed core-rule policy. Do not edit by hand.",
        "",
    ]
    lines.extend(_string_lines(name="GENERATED_POLICY_OWNERS", values=owners))
    for rule in rules:
        for constraint in sorted(rule.constraints, key=lambda item: item.name):
            lines.extend(_constraint_lines(code=rule.code, constraint=constraint))
        for limit in sorted(rule.limits, key=lambda item: item.name):
            lines.extend(_limit_lines(code=rule.code, limit=limit))
    source: str = "\n".join(lines).rstrip()
    return f"{source}\n".encode()


def serialized_cli_defaults() -> bytes:
    """Return deterministic Rust source for canonical configuration defaults."""

    lines: list[str] = [
        "//! Generated configuration defaults. Do not edit by hand.",
        "",
    ]
    lines.extend(
        _pair_lines(
            name="DEFAULT_THRESHOLDS",
            rust_type="(&str, u32)",
            values=tuple((name.value, value) for name, value in DEFAULT_THRESHOLDS.items()),
        )
    )
    lines.extend(
        _pair_lines(
            name="DEFAULT_CONTRACTS",
            rust_type="(&str, &str)",
            values=tuple(
                (pattern, str(behavior)) for pattern, behavior in DEFAULT_CONTRACTS.items()
            ),
        )
    )
    lines.extend(_string_lines(name="DEFAULT_TEST_PATHS", values=DEFAULT_TEST_PATHS))
    lines.extend(_string_lines(name="DEFAULT_TEST_SCOPES", values=DEFAULT_TEST_SCOPES))
    lines.extend(_string_lines(name="DEFAULT_SELECT", values=DEFAULT_SELECT))
    lines.extend(_string_lines(name="DEFAULT_WARN", values=DEFAULT_WARN))
    lines.extend(_string_lines(name="DEFAULT_IGNORE", values=DEFAULT_IGNORE))
    lines.extend(
        _value_line(
            name="DEFAULT_CACHE_ENABLED",
            rust_type="bool",
            value=DEFAULT_CACHE_ENABLED,
        )
    )
    lines.extend(
        _value_line(
            name="DEFAULT_CACHE_REQUIRE_CACHEABLE",
            rust_type="bool",
            value=DEFAULT_CACHE_REQUIRE_CACHEABLE,
        )
    )
    lines.extend(
        _value_line(
            name="DEFAULT_EXPERIMENTAL_MEMORY",
            rust_type="bool",
            value=DEFAULT_EXPERIMENTAL_MEMORY,
        )
    )
    lines.extend(
        _value_line(
            name="DEFAULT_MEMORY_ARCHIVE_DAYS",
            rust_type="u64",
            value=DEFAULT_MEMORY_TASKS_ARCHIVE_AFTER_DAYS,
        )
    )
    lines.extend(
        _value_line(
            name="SKILLS_METADATA_PROTOCOL_VERSION",
            rust_type="u32",
            value=SKILLS_METADATA_PROTOCOL_VERSION,
        )
    )
    lines.extend(_string_lines(name="CONFIG_ROLE_NAMES", values=tuple(sorted(CONFIG_ROLE_NAMES))))
    lines.extend(_string_lines(name="CONTRACT_BEHAVIORS", values=tuple(sorted(CONTRACT_BEHAVIORS))))
    lines.extend(
        _string_lines(
            name="RULE_CONFIGURATION_INPUTS",
            values=tuple(sorted(RULE_CONFIGURATION_INPUTS)),
        )
    )
    source: str = "\n".join(lines).rstrip()
    return f"{source}\n".encode()


def _constraint_lines(*, code: str, constraint: RuleConstraint) -> list[str]:
    name: str = re.sub(r"[^A-Z0-9_]", "_", f"{code}_{constraint.name.upper()}")
    lines: list[str] = ["#[rustfmt::skip]", f"pub(crate) const {name}: &[&str] = &["]
    lines.extend(f"    {json.dumps(value, ensure_ascii=False)}," for value in constraint.values)
    lines.extend(["];", ""])
    return lines


def _pair_lines(*, name: str, rust_type: str, values: tuple[tuple[str, object], ...]) -> list[str]:
    lines: list[str] = ["#[rustfmt::skip]", f"pub(crate) const {name}: &[{rust_type}] = &["]
    lines.extend(
        f"    ({json.dumps(key)}, {json.dumps(value) if isinstance(value, str) else value}),"
        for key, value in values
    )
    lines.extend(["];", ""])
    return lines


def _limit_lines(*, code: str, limit: RuleLimit) -> list[str]:
    name: str = re.sub(r"[^A-Z0-9_]", "_", f"{code}_{limit.name.upper()}")
    return [f"pub(crate) const {name}: usize = {limit.value};", ""]


def _value_line(*, name: str, rust_type: str, value: bool | int) -> list[str]:
    rendered: str = str(value).lower() if isinstance(value, bool) else str(value)
    return [f"pub(crate) const {name}: {rust_type} = {rendered};", ""]


def _string_lines(*, name: str, values: Sequence[str]) -> list[str]:
    lines: list[str] = ["#[rustfmt::skip]", f"pub(crate) const {name}: &[&str] = &["]
    lines.extend(f"    {json.dumps(value)}," for value in values)
    lines.extend(["];", ""])
    return lines
