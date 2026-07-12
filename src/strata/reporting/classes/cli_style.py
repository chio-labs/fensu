"""Semantic styling facade for human CLI output."""

from __future__ import annotations

from strata.reporting.constants import (
    ANSI_BOLD,
    ANSI_BOLD_CYAN,
    ANSI_BOLD_GREEN,
    ANSI_BOLD_RED,
    ANSI_DIM,
    ANSI_ORANGE,
    ANSI_RESET,
)


class CliStyle:
    """Apply the reporting theme by semantic output role."""

    def __init__(self, *, use_color: bool) -> None:
        self._use_color: bool = use_color

    def header_marker(self) -> str:
        return self._apply(text="-->", ansi=ANSI_BOLD_CYAN)

    def header_text(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_BOLD)

    def value(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_BOLD)

    def path(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_BOLD)

    def provenance(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_DIM)

    def hint(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_DIM)

    def absent(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_DIM)

    def success(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_BOLD_GREEN)

    def family_fault_code(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_ORANGE)

    def fault_count(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_BOLD_RED)

    def link(self, text: str) -> str:
        return self._apply(text=text, ansi=ANSI_BOLD_CYAN)

    def _apply(self, *, text: str, ansi: str) -> str:
        if not self._use_color:
            return text
        return f"{ansi}{text}{ANSI_RESET}"
