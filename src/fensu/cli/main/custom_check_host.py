"""Private whole-command host for checks containing custom Python rules."""

from __future__ import annotations

import sys
from typing import TextIO

from fensu.cli._helpers.check_command import execute_check


def run_custom_check(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run one custom-rule check and return its process exit code."""

    return execute_check(argv=argv, stdout=stdout, stderr=stderr)
