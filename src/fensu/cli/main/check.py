"""Run the fensu check command."""

from __future__ import annotations

import sys
from typing import TextIO

from fensu.cli._helpers.check_command import execute_check


def run_check(
    *,
    argv: tuple[str, ...] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run `fensu check` and return its process exit code."""

    return execute_check(argv=argv, stdout=stdout, stderr=stderr)
