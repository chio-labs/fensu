"""Validate a rule's metadata envelope and code namespace at definition time."""

from __future__ import annotations

import re

from strata.rules.authoring._helpers.code_grammar import rule_code_is_exact
from strata.rules.authoring.exceptions import RuleDefinitionError
from strata.rules.authoring.types import Family, RuleKind

_KEBAB_CASE_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_CORE_CODE_PREFIX: str = "SF"
_CUSTOM_CODE_PREFIX: str = "X"


def resolve_family(family: Family | str) -> Family:
    """Resolve a family value to a Family member or raise RuleDefinitionError."""

    if isinstance(family, Family):
        return family
    try:
        return Family(family)
    except ValueError as error:
        raise RuleDefinitionError(
            f"rule family must be one of {[member.value for member in Family]}; got {family!r}"
        ) from error


def resolve_envelope(*, code: str, slug: str, message: str, family: Family | str) -> Family:
    """Validate identity fields and return the resolved family, or raise."""

    resolved_family: Family = resolve_family(family)
    _validate_non_empty(field_name="code", value=code)
    _validate_code(code)
    _validate_slug(slug)
    _validate_non_empty(field_name="message", value=message)
    _validate_family_code_consistency(code=code, family=resolved_family)
    return resolved_family


def infer_kind(code: str) -> RuleKind:
    """Infer whether an already validated code is core or custom."""

    return RuleKind.CORE if code.startswith(_CORE_CODE_PREFIX) else RuleKind.CUSTOM


def validate_code_namespace(*, code: str, kind: RuleKind) -> None:
    """Enforce that exact codes use the namespace required by their kind."""

    if not rule_code_is_exact(code):
        raise RuleDefinitionError(f"rule code {code!r} must be one exact core or custom rule code")

    if kind is RuleKind.CUSTOM:
        if code.startswith(_CORE_CODE_PREFIX):
            raise RuleDefinitionError(
                f"custom rule code {code!r} must not start with {_CORE_CODE_PREFIX!r}; "
                f"custom codes use the {_CUSTOM_CODE_PREFIX!r} namespace"
            )
        if not code.startswith(_CUSTOM_CODE_PREFIX):
            raise RuleDefinitionError(
                f"custom rule code {code!r} must start with {_CUSTOM_CODE_PREFIX!r}"
            )
        return
    if not code.startswith(_CORE_CODE_PREFIX):
        raise RuleDefinitionError(f"core rule code {code!r} must start with {_CORE_CODE_PREFIX!r}")


def _validate_family_code_consistency(*, code: str, family: Family) -> None:
    if family is Family.CUSTOM and code.startswith(_CORE_CODE_PREFIX):
        raise RuleDefinitionError(
            f"rule code {code!r} declares the custom family but uses the core "
            f"{_CORE_CODE_PREFIX!r} namespace; custom rules must use the {_CUSTOM_CODE_PREFIX!r} "
            f"namespace"
        )


def _validate_code(code: str) -> None:
    if not rule_code_is_exact(code):
        raise RuleDefinitionError(f"rule code {code!r} must be one exact core or custom rule code")


def _validate_non_empty(*, field_name: str, value: str) -> None:
    if not value or not value.strip():
        raise RuleDefinitionError(f"rule {field_name} must be a non-empty string")


def _validate_slug(slug: str) -> None:
    _validate_non_empty(field_name="slug", value=slug)
    if not _KEBAB_CASE_PATTERN.fullmatch(slug):
        raise RuleDefinitionError(
            f"rule slug {slug!r} must be kebab-case (lowercase words joined by hyphens)"
        )
