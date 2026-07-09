"""The class-based authoring style: subclass Rule to define a core or custom rule."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from typing import ClassVar

from strata.rules.authoring.exceptions import RuleDefinitionError
from strata.rules.authoring.helpers.envelope import (
    infer_kind,
    resolve_envelope,
    validate_code_namespace,
)
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, Severity

_ENVELOPE_CLASS_VARS: tuple[str, ...] = ("code", "family", "slug", "message")


class Rule(ABC):
    """Base class for class-authored rules; validates its envelope at definition time."""

    code: ClassVar[str]
    family: ClassVar[Family | str]
    slug: ClassVar[str]
    message: ClassVar[str]
    remediation: ClassVar[str | None] = None
    severity: ClassVar[Severity] = Severity.ERROR
    enabled_by_default: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "__abstractmethods__", frozenset()):
            return
        missing: list[str] = [name for name in _ENVELOPE_CLASS_VARS if not hasattr(cls, name)]
        if missing:
            raise RuleDefinitionError(
                f"Rule subclass {cls.__name__!r} is missing required class attributes: "
                f"{', '.join(missing)}"
            )
        resolve_envelope(
            code=cls.code,
            slug=cls.slug,
            message=cls.message,
            family=cls.family,
        )
        validate_code_namespace(code=cls.code, kind=infer_kind(cls.code))

    @abstractmethod
    def check(self, *, module: ast.Module, ctx: RuleContext) -> list[Fault]:
        """Return the faults this rule finds in the given module."""
        ...

    def to_spec(self) -> RuleSpec:
        """Compile this rule instance into a uniform RuleSpec."""

        return RuleSpec(
            code=self.code,
            family=resolve_envelope(
                code=self.code,
                slug=self.slug,
                message=self.message,
                family=self.family,
            ),
            slug=self.slug,
            message=self.message,
            check=self.check,
            remediation=self.remediation,
            severity=self.severity,
            kind=infer_kind(self.code),
            enabled_by_default=self.enabled_by_default,
        )
