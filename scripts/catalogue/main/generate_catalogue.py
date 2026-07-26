"""Generate or verify the native core catalogue projection."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from fensu.cli._helpers.rule_metadata import serialized_rule_catalogue
from fensu.rules.catalog.constants import CORE_RULES
from scripts.catalogue._helpers.rust_policy import serialized_cli_defaults, serialized_native_policy
from scripts.catalogue.constants import (
    CATALOGUE_ASSET_PATH,
    CHECK_ARGUMENTS,
    CLI_DEFAULTS_PATH,
    NATIVE_POLICY_PATH,
    WRITE_ARGUMENTS,
)


def generate_catalogue(
    *,
    arguments: Sequence[str],
    catalogue_target: Path = CATALOGUE_ASSET_PATH,
    native_policy_target: Path = NATIVE_POLICY_PATH,
    cli_defaults_target: Path = CLI_DEFAULTS_PATH,
) -> int:
    """Write the canonical asset or verify that its committed bytes are current."""

    expected_catalogue: bytes = serialized_rule_catalogue(rules=CORE_RULES)
    expected_native_policy: bytes = serialized_native_policy(rules=CORE_RULES)
    expected_cli_defaults: bytes = serialized_cli_defaults()
    normalized: tuple[str, ...] = tuple(arguments)
    if normalized == CHECK_ARGUMENTS:
        current_catalogue: bytes | None = (
            catalogue_target.read_bytes() if catalogue_target.is_file() else None
        )
        current_native_policy: bytes | None = (
            native_policy_target.read_bytes() if native_policy_target.is_file() else None
        )
        current_cli_defaults: bytes | None = (
            cli_defaults_target.read_bytes() if cli_defaults_target.is_file() else None
        )
        if (
            current_catalogue == expected_catalogue
            and current_native_policy == expected_native_policy
            and current_cli_defaults == expected_cli_defaults
        ):
            return 0
        sys.stderr.write(
            "Generated rule assets are stale; run `uv run python -m scripts.catalogue_generate`\n"
        )
        return 1
    if normalized not in ((), WRITE_ARGUMENTS):
        sys.stderr.write("usage: python -m scripts.catalogue_generate [--check | --write]\n")
        return 2
    catalogue_target.parent.mkdir(parents=True, exist_ok=True)
    native_policy_target.parent.mkdir(parents=True, exist_ok=True)
    cli_defaults_target.parent.mkdir(parents=True, exist_ok=True)
    catalogue_target.write_bytes(expected_catalogue)
    native_policy_target.write_bytes(expected_native_policy)
    cli_defaults_target.write_bytes(expected_cli_defaults)
    return 0
