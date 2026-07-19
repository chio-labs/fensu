"""Classify whether a rule check reads the raw module parameter."""

from __future__ import annotations

import ast
import inspect
import textwrap

from fensu.rules.authoring.types import RuleCheck
from fensu.rules.catalog.constants import MODULE_PARAMETER_NAME


def check_uses_module(*, check: RuleCheck) -> bool:
    """Return whether a check body references module beyond deleting it."""

    try:
        source: str = textwrap.dedent(inspect.getsource(check))
        parsed: ast.Module = ast.parse(source)
    except (OSError, TypeError, SyntaxError, ValueError):
        return True
    for node in ast.walk(parsed):
        if (
            isinstance(node, ast.Name)
            and node.id == MODULE_PARAMETER_NAME
            and not isinstance(node.ctx, ast.Del)
        ):
            return True
    return False
