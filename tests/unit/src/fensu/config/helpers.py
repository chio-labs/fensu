"""Helpers for config loading tests."""

from __future__ import annotations

from pathlib import Path

from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import Family, RuleKind


def write_fensu_toml(*, root: Path, contents: str) -> Path:
    """Write a dedicated fensu.toml config file."""

    path: Path = root / "fensu.toml"
    path.write_text(contents, encoding="utf-8")
    return path


def write_pyproject_toml(*, root: Path, contents: str) -> Path:
    """Write a pyproject.toml config file."""

    path: Path = root / "pyproject.toml"
    path.write_text(contents, encoding="utf-8")
    return path


def write_custom_rule_file(*, root: Path, relative_path: str, contents: str) -> Path:
    """Write one repository-local custom rule file."""

    path: Path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


def make_config_rule(*, code: str, options: tuple[RuleOption[object], ...] = ()) -> RuleSpec:
    """Build one inert custom rule specification for config resolution tests."""

    return RuleSpec(
        code=code,
        family=Family.CUSTOM,
        slug=f"rule-{code.lower()}",
        message=f"rule {code}",
        kind=RuleKind.CUSTOM,
        enabled_by_default=False,
        options=options,
    )
