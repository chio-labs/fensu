"""Recognize one deterministic public API facade."""

from __future__ import annotations

import ast

from fensu.analysis._helpers.public_facades import is_public_facade as _is_public_facade


def is_public_facade_source(*, source: str, package_name: str) -> bool:
    """Return whether Python source defines a statically bounded public API facade."""

    return _is_public_facade(module=ast.parse(source), package_name=package_name)
