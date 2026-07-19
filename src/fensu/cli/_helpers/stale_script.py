"""Detect obsolete Python-owned console scripts after package upgrades."""

from __future__ import annotations

import sys
from pathlib import Path

from fensu.cli.constants import CONSOLE_SCRIPT_NAMES


def is_stale_console_script() -> bool:
    """Return whether argv names an obsolete generated Python wrapper."""

    path: Path = Path(sys.argv[0])
    if path.name not in CONSOLE_SCRIPT_NAMES or not path.is_file():
        return False
    try:
        return path.read_bytes().startswith(b"#!")
    except OSError:
        return False
