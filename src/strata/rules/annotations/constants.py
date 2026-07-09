"""Annotation rule catalogue constants."""

from __future__ import annotations

from strata.rules.annotations.main.annotation_rules import annotation_rules
from strata.rules.authoring.models import RuleSpec

SFA_RULES: tuple[RuleSpec, ...] = tuple(sorted(annotation_rules(), key=lambda rule: rule.code))
