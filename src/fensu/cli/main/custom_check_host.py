"""Private whole-command host for checks containing custom Python rules."""

from __future__ import annotations

import json
import os
import sys
from typing import TextIO, cast

from fensu.cli._helpers.check_command import execute_check
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
