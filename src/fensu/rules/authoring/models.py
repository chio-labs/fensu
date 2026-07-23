"""Authoring structured runtime models: the fault and the compiled rule spec."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fensu.rules.authoring.constants import MISSING
from fensu.rules.authoring.types import (
    ExecutionOwner,
    Family,
    Missing,
    RuleCheck,
    RuleKind,
    RuleOptionKind,
    Severity,
)


@dataclass(frozen=True, slots=True, eq=False)
class RuleOption[T]:
    """One immutable typed option declaration owned by a rule."""

    name: str
    kind: RuleOptionKind
    default: T | Missing = MISSING
    required: bool = False
    description: str | None = None
    choices: tuple[str, ...] | None = None
    minimum: int | None = None
    maximum: int | None = None
    minimum_items: int | None = None

    def __post_init__(self) -> None:
        """Reject invalid declarations and defaults at authoring time."""

        from fensu.rules.authoring._helpers.options import validate_option_declaration

        validate_option_declaration(option=self)

    @classmethod
    def boolean(
        cls,
        *,
        name: str,
        default: bool | Missing = MISSING,
        required: bool = False,
        description: str | None = None,
    ) -> RuleOption[bool]:
        """Declare a boolean rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.BOOLEAN,
            default=default,
            required=required,
            description=description,
        )

    @classmethod
    def integer(
        cls,
        *,
        name: str,
        default: int | Missing = MISSING,
        required: bool = False,
        minimum: int | None = None,
        maximum: int | None = None,
        description: str | None = None,
    ) -> RuleOption[int]:
        """Declare a signed 64-bit integer rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.INTEGER,
            default=default,
            required=required,
            description=description,
            minimum=minimum,
            maximum=maximum,
        )

    @classmethod
    def string(
        cls,
        *,
        name: str,
        default: str | Missing = MISSING,
        required: bool = False,
        choices: tuple[str, ...] | None = None,
        description: str | None = None,
    ) -> RuleOption[str]:
        """Declare a string rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.STRING,
            default=default,
            required=required,
            description=description,
            choices=choices,
        )

    @classmethod
    def string_list(
        cls,
        *,
        name: str,
        default: tuple[str, ...] | Missing = MISSING,
        required: bool = False,
        minimum_items: int | None = None,
        description: str | None = None,
    ) -> RuleOption[tuple[str, ...]]:
        """Declare an immutable string-list rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.STRING_LIST,
            default=default,
            required=required,
            description=description,
            minimum_items=minimum_items,
        )

    @classmethod
    def integer_list(
        cls,
        *,
        name: str,
        default: tuple[int, ...] | Missing = MISSING,
        required: bool = False,
        minimum_items: int | None = None,
        description: str | None = None,
    ) -> RuleOption[tuple[int, ...]]:
        """Declare an immutable integer-list rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.INTEGER_LIST,
            default=default,
            required=required,
            description=description,
            minimum_items=minimum_items,
        )


@dataclass(frozen=True, slots=True)
class Fault:
    """A single rule finding against a file."""

    code: str
    path: Path
    message: str
    line: int | None = None
    column: int | None = None
    remediation: str | None = None

    def format(self, root: Path) -> str:
        """Render the fault as `path:line:col: CODE message` relative to root."""

        try:
            relative_path: Path = self.path.relative_to(root)
        except ValueError:
            relative_path = self.path
        line_text: str = str(self.line) if self.line is not None else "-"
        column_text: str = str(self.column) if self.column is not None else "-"
        return f"{relative_path.as_posix()}:{line_text}:{column_text}: {self.code} {self.message}"


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """The compiled, uniform representation of a core or custom rule."""

    code: str
    family: Family
    slug: str
    message: str
    check: RuleCheck | None = None
    remediation: str | None = None
    severity: Severity = Severity.ERROR
    kind: RuleKind = RuleKind.CORE
    source: str | None = None
    enabled_by_default: bool = True
    cacheable: bool | None = None
    uses_module: bool = False
    execution_owner: ExecutionOwner = ExecutionOwner.FILE
    options: tuple[RuleOption[object], ...] = ()


@dataclass(frozen=True, slots=True)
class CustomRuleRegistration:
    """One configured custom rule tied to its repository declaration owner."""

    rule: RuleSpec
    source_path: Path
    module_name: str
    function_name: str
    declaration_line: int
    declaration_column: int
    owner_key: str
