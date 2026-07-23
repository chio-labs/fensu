"""Validate declarations and resolve canonical immutable rule-option values."""

from __future__ import annotations

from fensu.rules.authoring.constants import (
    MAXIMUM_OPTION_INTEGER,
    MINIMUM_OPTION_INTEGER,
    MISSING,
    OPTION_NAME_PATTERN,
)
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import RuleOption
from fensu.rules.authoring.types import RuleOptionKind, RuleOptionValue


def validate_option_declaration(*, option: RuleOption[object]) -> None:
    """Reject malformed declarations and rule-authored defaults."""

    if not isinstance(option.name, str) or not OPTION_NAME_PATTERN.fullmatch(option.name):
        raise RuleDefinitionError(f"rule option name {option.name!r} must use lowercase snake case")
    if not isinstance(option.kind, RuleOptionKind):
        raise RuleDefinitionError(f"rule option {option.name} must use a supported option kind")
    if type(option.required) is not bool:
        raise RuleDefinitionError(f"rule option {option.name} required must be a boolean")
    if option.required and option.default is not MISSING:
        raise RuleDefinitionError(
            f"rule option {option.name} cannot be required and define a default"
        )
    if not option.required and option.default is MISSING:
        raise RuleDefinitionError(f"rule option {option.name} must define a default or be required")
    if option.description is not None and (
        not isinstance(option.description, str) or not option.description.strip()
    ):
        raise RuleDefinitionError(f"rule option {option.name} description must be non-empty")
    _validate_choices(option=option)
    _validate_constraints(option=option)
    if option.default is not MISSING:
        _ = get_rule_option_value(option=option, value=option.default, authoring=True)


def get_rule_option_value(
    *, option: RuleOption[object], value: object, authoring: bool = False
) -> RuleOptionValue:
    """Return one canonical immutable option value or raise the owning error type."""

    error_type: type[Exception] = RuleDefinitionError if authoring else ValueError
    kind: RuleOptionKind = option.kind
    if kind is RuleOptionKind.BOOLEAN and type(value) is bool:
        return value
    if kind is RuleOptionKind.INTEGER and type(value) is int and _integer_in_range(value):
        _validate_integer_value(option=option, value=value, error_type=error_type)
        return value
    if kind is RuleOptionKind.STRING and isinstance(value, str):
        if option.choices is not None and value not in option.choices:
            choices: str = ", ".join(option.choices)
            raise error_type(f"rule option {option.name} must be one of: {choices}")
        return value
    if kind in {RuleOptionKind.STRING_LIST, RuleOptionKind.INTEGER_LIST}:
        return _get_list_value(option=option, value=value, error_type=error_type)
    raise error_type(f"rule option {option.name} must be {_option_type_name(kind)}")


def _validate_choices(*, option: RuleOption[object]) -> None:
    if option.choices is None:
        return
    if option.kind is not RuleOptionKind.STRING:
        raise RuleDefinitionError(f"rule option {option.name} choices require a string option")
    if not isinstance(option.choices, tuple):
        raise RuleDefinitionError(f"rule option {option.name} choices must be an immutable tuple")
    if not option.choices or len(set(option.choices)) != len(option.choices):
        raise RuleDefinitionError(f"rule option {option.name} choices must be non-empty and unique")
    if any(not isinstance(choice, str) for choice in option.choices):
        raise RuleDefinitionError(f"rule option {option.name} choices must contain only strings")


def _validate_constraints(*, option: RuleOption[object]) -> None:
    if option.kind is not RuleOptionKind.INTEGER and (
        option.minimum is not None or option.maximum is not None
    ):
        raise RuleDefinitionError(f"rule option {option.name} bounds require an integer option")
    if option.kind not in {RuleOptionKind.STRING_LIST, RuleOptionKind.INTEGER_LIST} and (
        option.minimum_items is not None
    ):
        raise RuleDefinitionError(f"rule option {option.name} minimum_items requires a list option")
    for name, value in (("minimum", option.minimum), ("maximum", option.maximum)):
        if value is not None and (type(value) is not int or not _integer_in_range(value)):
            raise RuleDefinitionError(
                f"rule option {option.name} {name} must be a signed 64-bit integer"
            )
    if (
        option.minimum is not None
        and option.maximum is not None
        and option.minimum > option.maximum
    ):
        raise RuleDefinitionError(f"rule option {option.name} minimum cannot exceed maximum")
    if option.minimum_items is not None and (
        type(option.minimum_items) is not int or option.minimum_items < 0
    ):
        raise RuleDefinitionError(f"rule option {option.name} minimum_items must be non-negative")


def _validate_integer_value(
    *, option: RuleOption[object], value: int, error_type: type[Exception]
) -> None:
    if option.minimum is not None and value < option.minimum:
        raise error_type(f"rule option {option.name} must be at least {option.minimum}")
    if option.maximum is not None and value > option.maximum:
        raise error_type(f"rule option {option.name} must be at most {option.maximum}")


def _get_list_value(
    *, option: RuleOption[object], value: object, error_type: type[Exception]
) -> RuleOptionValue:
    if not isinstance(value, (list, tuple)) or (
        error_type is RuleDefinitionError and isinstance(value, list)
    ):
        raise error_type(f"rule option {option.name} must be {_option_type_name(option.kind)}")
    if option.minimum_items is not None and len(value) < option.minimum_items:
        raise error_type(
            f"rule option {option.name} must contain at least {option.minimum_items} item(s)"
        )
    if option.kind is RuleOptionKind.STRING_LIST:
        if any(type(item) is not str for item in value):
            raise error_type(f"rule option {option.name} must be an array of strings")
        return tuple(item for item in value if isinstance(item, str))
    if any(type(item) is not int for item in value):
        raise error_type(f"rule option {option.name} must be an array of integers")
    integers: tuple[int, ...] = tuple(item for item in value if type(item) is int)
    if any(not _integer_in_range(item) for item in integers):
        raise error_type(f"rule option {option.name} integers must fit signed 64-bit range")
    return integers


def _integer_in_range(value: int) -> bool:
    return MINIMUM_OPTION_INTEGER <= value <= MAXIMUM_OPTION_INTEGER


def _option_type_name(kind: RuleOptionKind) -> str:
    return {
        RuleOptionKind.BOOLEAN: "a boolean",
        RuleOptionKind.INTEGER: "an integer",
        RuleOptionKind.STRING: "a string",
        RuleOptionKind.STRING_LIST: "an array of strings",
        RuleOptionKind.INTEGER_LIST: "an array of integers",
    }[kind]
