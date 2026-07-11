"""Strata: an architecture linter for Python repos, with a public rule-authoring API."""

from __future__ import annotations

from strata.rules.authoring.main.define import rule
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import Family, RuleContext, Severity, Threshold

__all__ = ["Fault", "Family", "Severity", "Threshold", "rule", "RuleContext"]
