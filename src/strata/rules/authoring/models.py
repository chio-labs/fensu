"""Authoring structured runtime models: the fault and the compiled rule spec."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.rules.authoring.types import Family, RuleCheck, RuleKind, Severity


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
        return f"{relative_path}:{line_text}:{column_text}: {self.code} {self.message}"


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """The compiled, uniform representation of a core or custom rule."""

    code: str
    family: Family
    slug: str
    message: str
    check: RuleCheck
    remediation: str | None = None
    severity: Severity = Severity.ERROR
    kind: RuleKind = RuleKind.CORE
    source: str | None = None
    enabled_by_default: bool = True
    cacheable: bool | None = None
    uses_module: bool = False


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
