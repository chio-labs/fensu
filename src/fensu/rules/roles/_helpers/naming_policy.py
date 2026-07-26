"""Fixed naming-policy values for role rules."""

from __future__ import annotations


def get_forbidden_module_filenames() -> tuple[str, ...]:
    """Return exhaustive module filenames rejected by FFR201."""

    return ("misc.py",)


def get_forbidden_package_names() -> tuple[str, ...]:
    """Return exhaustive package names rejected by FFR204."""

    return "base", "common", "helpers", "lib", "misc", "shared", "util", "utils"
