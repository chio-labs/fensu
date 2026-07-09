"""Tests rule constants."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.tests.main.testing_rules import test_rules

SFT_RULES: tuple[RuleSpec, ...] = test_rules()
