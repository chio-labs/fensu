"""Private process entry for Python-authored rules over native web facts."""

from __future__ import annotations

import json
import sys
from importlib.metadata import version
from typing import TextIO

from fensu.cli._helpers.web_custom_rule_host import build_web_custom_response
from fensu.cli.constants import WEB_CUSTOM_HOST_PROTOCOL_VERSION


def run_web_custom_rule_protocol(*, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Read one native request and write one bounded structured response."""

    runtime_version: str = version("fensu")
    try:
        request: object = json.load(stdin)
        response: dict[str, object] = build_web_custom_response(
            request=request, runtime_version=runtime_version
        )
    except Exception as error:
        response = {
            "protocol": WEB_CUSTOM_HOST_PROTOCOL_VERSION,
            "runtime_version": runtime_version,
            "error": str(error),
            "payload": None,
            "messages": [],
        }
    json.dump(response, stdout, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    stdout.write("\n")
    return 0
