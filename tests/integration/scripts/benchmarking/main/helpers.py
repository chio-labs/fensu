"""Filesystem helpers for benchmark tooling tests."""

import subprocess
import sys
from pathlib import Path


def write_fake_strata(*, root: Path, output: str, changing: bool = False) -> Path:
    """Write a fake Strata executable with stable or changing diagnostics."""

    executable: Path = root / "strata"
    changing_body: str = (
        '#!/bin/bash\nstate="$PWD/.count"\ncount=0\n'
        'if [[ -f "$state" ]]; then count=$(<"$state"); fi\n'
        'count=$((count + 1))\nprintf "%s" "$count" > "$state"\n'
        'printf "Found %s faults\\n" "$count"\nexit 1\n'
    )
    escaped: str = output.replace("'", "'\\''")
    stable_body: str = f"#!/bin/bash\nprintf '%s' '{escaped}'\nexit 1\n"
    body: str = {False: stable_body, True: changing_body}[changing]
    executable.write_text(body, encoding="utf-8")
    executable.chmod(0o755)
    return executable


def run_benchmark_command(
    *, project: Path, executable: Path, runs: int
) -> subprocess.CompletedProcess[str]:
    """Run the public benchmark command against a fake Strata executable."""

    return subprocess.run(
        (
            sys.executable,
            "-m",
            "scripts.benchmark_check",
            "--project",
            str(project),
            "--runs",
            str(runs),
            "--executable",
            str(executable),
        ),
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )


def write_profile_project(root: Path) -> None:
    """Write a minimal project for an in-process profile run."""

    source: Path = root / "src/pkg/domain/core/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    (root / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\ntooling = []\nselect = ["SFR601"]\n'
        '[[threshold_overrides]]\npaths = ["src/pkg/**/*.py"]\n'
        'reason = "Profile rendering."\nthresholds = { max_file_lines = 2 }\n',
        encoding="utf-8",
    )
