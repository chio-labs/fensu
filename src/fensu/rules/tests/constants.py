"""Tests rule constants."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.tests.main._testing_rules import test_rules

FFT_RULES: tuple[RuleSpec, ...] = test_rules()
