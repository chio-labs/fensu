"""Run the strata init command."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TextIO

from strata.cli.constants import NO_COLOR_ENVIRONMENT_VARIABLE
from strata.config.exceptions import ConfigError
from strata.scaffolding.exceptions import InitRefusalError
from strata.scaffolding.main.find_local_config import find_local_config
from strata.scaffolding.main.run_init import run_init as _run_init
from strata.scaffolding.models import InitOptions
from strata.scaffolding.types import AdoptionMode


def run_init(
    *,
    argv: tuple[str, ...] | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    working_directory: Path | None = None,
    home_dir: Path | None = None,
) -> int:
    """Parse `strata init` options and delegate repository initialization."""

    args: argparse.Namespace = _parser().parse_args(() if argv is None else argv)
    options: InitOptions = _options(args=args)
    repository: Path = (working_directory or Path.cwd()).resolve()
    try:
        existing_config: Path | None = find_local_config(repository=repository)
    except (ConfigError, InitRefusalError, OSError) as error:
        stderr.write(f"{error}\n")
        return 2
    if existing_config is not None:
        stdout.write(f"Strata configuration already exists: {existing_config} (nothing to do)\n")
        return 0
    use_color: bool = stdout.isatty() and NO_COLOR_ENVIRONMENT_VARIABLE not in os.environ
    return _run_init(
        repository=repository,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        options=options,
        use_color=use_color,
        home_dir=home_dir,
    )


def _parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="strata init")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--root", dest="roots", action="extend", nargs="+")
    parser.add_argument("--tests", action="extend", nargs="+")
    parser.add_argument("--tooling", action="extend", nargs="+")
    adoption: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    adoption.add_argument(
        "--full",
        dest="adoption",
        action="store_const",
        const=AdoptionMode.FULL,
    )
    adoption.add_argument(
        "--gradual",
        dest="adoption",
        action="store_const",
        const=AdoptionMode.GRADUAL,
    )
    skills: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    skills.add_argument("--skills", dest="skills", action="store_true")
    skills.add_argument("--no-skills", dest="skills", action="store_false")
    parser.set_defaults(skills=None)
    parser.add_argument("--name")
    return parser


def _options(*, args: argparse.Namespace) -> InitOptions:
    return InitOptions(
        yes=args.yes,
        roots=None if args.roots is None else tuple(args.roots),
        tests=None if args.tests is None else tuple(args.tests),
        tooling=None if args.tooling is None else tuple(args.tooling),
        adoption=args.adoption,
        skills=args.skills,
        name=args.name,
    )
