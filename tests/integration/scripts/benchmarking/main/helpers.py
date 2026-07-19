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


def run_profile_benchmark_command(*, project: Path) -> subprocess.CompletedProcess[str]:
    """Run the public profiler command against an external custom-rule project."""

    return subprocess.run(
        (
            sys.executable,
            "-m",
            "scripts.benchmark_check",
            "--project",
            str(project),
            "--profile",
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


def write_custom_rule_profile_project(*, root: Path, rule_code: str) -> None:
    """Write an external profile project whose scripts package conflicts with Strata's."""

    source: Path = root / "src/pkg/models.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    package: Path = root / "scripts/policy"
    package.mkdir(parents=True)
    (root / "scripts/__init__.py").write_text('"""External scripts."""\n', encoding="utf-8")
    (package / "__init__.py").write_text('"""External policy."""\n', encoding="utf-8")
    (package / "rules.py").write_text(
        f'''import sys

from strata import Family, Fault, RuleContext, rule


if not sys.dont_write_bytecode:
    raise RuntimeError("profiler must keep the external repository bytecode-free")


@rule(code="{rule_code}", family=Family.CUSTOM, slug="profile-rule", message="profile rule")
def profile_rule(*, module: object, ctx: RuleContext) -> list[Fault]:
    del module, ctx
    return []
''',
        encoding="utf-8",
    )
    (root / "strata.toml").write_text(
        f'roots = ["src/pkg"]\ntests = []\ntooling = []\nselect = ["{rule_code}"]\n'
        'rule_modules = ["scripts.policy.rules"]\n',
        encoding="utf-8",
    )
