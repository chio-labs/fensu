"""Private whole-command host for checks containing custom Python rules."""

from __future__ import annotations

import json
import os
import sys
from typing import TextIO, cast

from fensu.cli._helpers.check_command import execute_check, execute_structured_check
from fensu.cli.constants import CUSTOM_CHECK_TARGETS_ENVIRONMENT_VARIABLE
from fensu.cli.exceptions import CliCommandError


def run_custom_check(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run one custom-rule check and return its process exit code."""

    encoded_targets: str | None = os.environ.get(CUSTOM_CHECK_TARGETS_ENVIRONMENT_VARIABLE)
    target_names: tuple[str | None, ...] | None = None
    if encoded_targets is not None:
        decoded_targets: object = json.loads(encoded_targets)
        if not isinstance(decoded_targets, list) or not all(
            isinstance(value, str) for value in decoded_targets
        ):
            raise CliCommandError("Internal custom-check targets must be a JSON string array.")
        target_names = cast("tuple[str | None, ...]", tuple(decoded_targets))
    return execute_check(
        argv=argv,
        stdout=stdout,
        stderr=stderr,
        target_names=target_names,
    )


def _run_custom_check_protocol(*, argv: tuple[str, ...] | None = None) -> int:
    """Write one versioned structured response for native aggregate rendering."""

    encoded_targets: str | None = os.environ.get(CUSTOM_CHECK_TARGETS_ENVIRONMENT_VARIABLE)
    decoded_targets: object = json.loads(encoded_targets or "[]")
    if not isinstance(decoded_targets, list) or not all(
        isinstance(value, str) for value in decoded_targets
    ):
        raise CliCommandError("Internal custom-check targets must be a JSON string array.")
    response: dict[str, object] = execute_structured_check(
        argv=() if argv is None else argv,
        target_names=(
            cast("tuple[str | None, ...]", tuple(decoded_targets)) if decoded_targets else (None,)
        ),
    )
    json.dump(response, sys.stdout, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    sys.stdout.write("\n")
    return 0
