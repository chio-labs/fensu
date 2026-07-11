"""Filesystem and subprocess helpers for CLI end-to-end tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.e2e.src.strata.cli.main._test_types import ConfigurableLayoutCliTestCase


def run_configurable_layout_case(
    *, root: Path, test_case: ConfigurableLayoutCliTestCase
) -> subprocess.CompletedProcess[str]:
    """Write a complete project and run the installed Strata console command."""

    (root / "strata.toml").write_text(test_case.config, encoding="utf-8")
    for file in test_case.files:
        path: Path = root / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.source, encoding="utf-8")
    working_directory: Path = root / test_case.working_directory
    working_directory.mkdir(parents=True, exist_ok=True)
    environment: dict[str, str] = dict(os.environ)
    environment["NO_COLOR"] = "1"
    return subprocess.run(
        (str(Path(sys.executable).with_name("strata")), *test_case.argv),
        cwd=working_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
