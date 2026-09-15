"""Evaluation exceptions."""

from __future__ import annotations

from pathlib import Path


class ModuleUnavailableError(Exception):
    """Raised when a rule declared module-free reads the raw module parameter."""


class ProjectContextUnavailableError(RuntimeError):
    """Raised when a project rule requests facts that require a current file."""


class ProjectQueryTypeError(TypeError):
    """Raised when a project query receives an unsupported path type."""


class ProjectAnalysisUnavailableError(RuntimeError):
    """Raised when fresh evaluation lacks its required project analysis."""


class NativeCoreCallbackError(RuntimeError):
    """Raised when native evaluation omits a selected core rule result."""


class RuleCallbackUnavailableError(RuntimeError):
    """Raised when a non-core rule has no executable callback."""


class RustCustomRuleError(RuntimeError):
    """Raised when a hosted Rust rule violates its callback or confinement contract."""


class WebCustomRuleError(RuntimeError):
    """Raised when a hosted web rule violates its callback or confinement contract."""


class ParseError(Exception):
    """Raised when a Python file cannot be parsed by the running interpreter."""

    def __init__(self, *, path: Path, message: str, line: int | None, column: int | None) -> None:
        """Store parse diagnostic location and text."""

        super().__init__(message)
        self.path: Path = path
        self.message: str = message
        self.line: int | None = line
        self.column: int | None = column
