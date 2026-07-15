"""Filesystem helpers for benchmark tooling tests."""

import subprocess
import sys
from pathlib import Path


def write_fake_strata(*, root: Path, output: str, changing: bool = False) -> Path:
    """Write a fake Strata executable with stable or changing diagnostics."""

    check_script: Path = root / "check"
    changing_body: str = (
        "import sys\n"
        "from pathlib import Path\n"
        'state = Path.cwd() / ".count"\n'
        "count = int(state.read_text()) if state.is_file() else 0\n"
        "count += 1\n"
        "state.write_text(str(count))\n"
        'sys.stdout.buffer.write(f"Found {count} faults\\n".encode("utf-8"))\n'
        "raise SystemExit(1)\n"
    )
    output_bytes: bytes = output.encode("utf-8")
    stable_body: str = (
        f"import sys\nsys.stdout.buffer.write({output_bytes!r})\nraise SystemExit(1)\n"
    )
    body: str = {False: stable_body, True: changing_body}[changing]
    check_script.write_text(body, encoding="utf-8")
    return Path(sys.executable)


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
