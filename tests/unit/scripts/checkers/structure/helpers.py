from pathlib import Path
from textwrap import dedent

from scripts.checkers.structure.structure_conventions.checker import check_paths
from scripts.checkers.structure.structure_conventions.models import Violation


def base_repo_files() -> dict[str, str]:
    return {
        "pyproject.toml": "[project]\nname = 'tmp'\nversion = '0.0.0'\n",
        "src/strata/__init__.py": '"""strata."""\n',
        "src/strata/example/__init__.py": '"""Example domain package."""\n',
        "scripts/__init__.py": '"""Repo scripts."""\n',
        "scripts/example_tool/__init__.py": '"""Example script package."""\n',
    }


def compliant_repo_files() -> dict[str, str]:
    return base_repo_files() | {
        "src/strata/example/widget/__init__.py": '"""Widget domain."""\n',
        "src/strata/example/widget/main/__init__.py": '"""Widget entries."""\n',
        "src/strata/example/widget/main/load.py": dedent(
            """
            from strata.example.widget.constants import DEFAULT_NAME
            from strata.example.widget.models import ExampleModel


            def load_example() -> ExampleModel:
                return ExampleModel(name=DEFAULT_NAME)
            """
        ).strip()
        + "\n",
        "src/strata/example/widget/types.py": dedent(
            """
            from enum import Enum
            from typing import TypeAlias


            class ExampleKind(Enum):
                BASIC = "basic"


            ExampleName: TypeAlias = str
            """
        ).strip()
        + "\n",
        "src/strata/example/widget/models.py": dedent(
            """
            from dataclasses import dataclass


            @dataclass(frozen=True)
            class ExampleModel:
                name: str
            """
        ).strip()
        + "\n",
        "src/strata/example/widget/constants.py": 'DEFAULT_NAME = "demo"\n',
        "scripts/example_tool/main.py": dedent(
            """
            from scripts.example_tool.constants import EXIT_CODE


            def main() -> int:
                return EXIT_CODE
            """
        ).strip()
        + "\n",
        "scripts/example_tool/constants.py": "EXIT_CODE = 0\n",
    }


def collect_violation_codes(repo_root: Path) -> tuple[str, ...]:
    violations: list[Violation] = check_paths(
        [repo_root / "src", repo_root / "scripts"], repo_root=repo_root
    )
    return tuple(violation.code for violation in violations)
