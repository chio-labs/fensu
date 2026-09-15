"""Private process entry for cross-target repository custom rules."""

from __future__ import annotations

import json
import sys
from importlib.metadata import version
from typing import TextIO

from fensu.cli._helpers.repository_custom_rule_host import (
    build_repository_custom_response,
)
from fensu.cli.constants import REPOSITORY_CUSTOM_HOST_PROTOCOL_VERSION


def run_repository_custom_rule_protocol(
    *, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout
) -> int:
    """Read one native request and write one bounded structured response."""

    runtime_version: str = version("fensu")
    try:
        request: object = json.load(stdin)
        response: dict[str, object] = build_repository_custom_response(
            request=request, runtime_version=runtime_version
        )
    except Exception as error:
        response = {
            "protocol": REPOSITORY_CUSTOM_HOST_PROTOCOL_VERSION,
            "runtime_version": runtime_version,
            "error": str(error),
            "payload": None,
            "messages": [],
        }
    json.dump(response, stdout, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    stdout.write("\n")
    return 0
