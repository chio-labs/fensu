"""Strata: an architecture linter for Python repos, with a public rule-authoring API."""

from __future__ import annotations

from strata.rules.authoring.classes.rule import Rule
from strata.rules.authoring.main.define import rule
from strata.rules.spec.models import Fault
from strata.rules.spec.types import Family, RuleContext, Severity

__all__ = ["Fault", "Family", "Severity", "Rule", "rule", "RuleContext"]
