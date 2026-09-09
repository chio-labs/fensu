"""Build final configuration after complete rule-catalogue discovery."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from fensu.config._helpers.defaults import build_config as build_validated_config
from fensu.config._helpers.rule_options import resolve_rule_options
from fensu.config._helpers.validate import validate_config
from fensu.config.models import Config
from fensu.config.types import AnalyzerId
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import RuleOptionValue


def build_config_for_rules(
    *,
    raw: Mapping[str, object],
    rules: tuple[RuleSpec, ...],
    analyzer: AnalyzerId = AnalyzerId.PYTHON,
) -> Config:
    """Validate declarations and overrides and return final immutable configuration."""

    validate_config(raw=raw, analyzer=analyzer)
    resolved: Mapping[str, Mapping[str, RuleOptionValue]] = resolve_rule_options(
        raw=raw.get("rule_options"), rules=rules
    )
    return replace(
        build_validated_config(raw=raw, rule_options=resolved, analyzer=analyzer),
        analyzer=analyzer,
    )
