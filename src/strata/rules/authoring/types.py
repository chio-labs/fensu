"""Authoring type-layer declarations."""

from __future__ import annotations

import ast
from collections.abc import Callable

from strata.rules.spec.models import Fault
from strata.rules.spec.types import RuleContext

type RuleCheck = Callable[[ast.Module, RuleContext], list[Fault]]
