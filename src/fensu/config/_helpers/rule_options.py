"""Resolve rule-authored defaults and repository overrides into immutable values."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import cast

from fensu.config.exceptions import ConfigValidationError
from fensu.rules.authoring.constants import MISSING
from fensu.rules.authoring.main.get_rule_option_value import get_rule_option_value
from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import RuleOptionValue


def resolve_rule_options(
    *, raw: object, rules: tuple[RuleSpec, ...]
) -> Mapping[str, Mapping[str, RuleOptionValue]]:
    """Validate all declarations and overrides and return current values by rule code."""

    raw_by_code: Mapping[object, object] = (
        cast(Mapping[object, object], raw) if isinstance(raw, Mapping) else {}
    )
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in rules}
    unknown_codes: list[str] = sorted(
        str(code) for code in raw_by_code if code not in rules_by_code
    )
    if unknown_codes:
        raise ConfigValidationError(f"Unknown rule option code {unknown_codes[0]}.")
    resolved: dict[str, Mapping[str, RuleOptionValue]] = {}
    for rule in rules:
        raw_values: object = raw_by_code.get(rule.code)
        if raw_values is not None and not rule.options:
            raise ConfigValidationError(f"Rule {rule.code} does not declare any options.")
        declarations: dict[str, RuleOption[object]] = _declarations(rule=rule)
        overrides: Mapping[object, object] = (
            cast(Mapping[object, object], raw_values) if isinstance(raw_values, Mapping) else {}
        )
        unknown_names: list[str] = sorted(
            str(name) for name in overrides if name not in declarations
        )
        if unknown_names:
            raise ConfigValidationError(f"Unknown option {unknown_names[0]} for rule {rule.code}.")
        current: dict[str, RuleOptionValue] = {}
        for name, option in declarations.items():
            if name in overrides:
                value: object = overrides[name]
            elif option.default is not MISSING:
                value = option.default
            else:
                raise ConfigValidationError(
                    f"Required option {name} for rule {rule.code} is missing."
                )
            try:
                current[name] = get_rule_option_value(option=option, value=value)
            except ValueError as error:
                detail: str = str(error).removeprefix(f"rule option {name} ")
                raise ConfigValidationError(f"Rule {rule.code} option {name} {detail}.") from error
        if current:
            resolved[rule.code] = MappingProxyType(current)
    return MappingProxyType(resolved)


def _declarations(*, rule: RuleSpec) -> dict[str, RuleOption[object]]:
    declarations: dict[str, RuleOption[object]] = {}
    for option in rule.options:
        if option.name in declarations:
            raise ConfigValidationError(
                f"Rule {rule.code} declares duplicate option {option.name}."
            )
        declarations[option.name] = option
    return declarations
