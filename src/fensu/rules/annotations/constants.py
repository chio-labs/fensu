"""Annotation rule catalogue constants."""

from __future__ import annotations

from fensu.rules.annotations.main._annotation_rules import annotation_rules
from fensu.rules.authoring.models import RuleSpec

FFA_RULES: tuple[RuleSpec, ...] = tuple(sorted(annotation_rules(), key=lambda rule: rule.code))
