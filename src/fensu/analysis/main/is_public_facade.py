"""Recognize one deterministic public API facade."""

from __future__ import annotations

import ast

from fensu.analysis._helpers.public_facades import is_public_facade as _is_public_facade


def is_public_facade(*, module: ast.Module, package_name: str) -> bool:
    """Return whether a module is a statically bounded public API facade."""

    return _is_public_facade(module=module, package_name=package_name)
