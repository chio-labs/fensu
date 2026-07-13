"""Render role-content examples supported by active core rules."""

from __future__ import annotations

from strata.agentdocs.constants import (
    RUNTIME_CLASSES_CODES,
    RUNTIME_CONSTANTS_CODES,
    RUNTIME_EXCEPTIONS_CODES,
    RUNTIME_FROZEN_MODEL_CODES,
    RUNTIME_HELPERS_CODES,
    RUNTIME_HELPERS_CONTENT_CODES,
    RUNTIME_MAIN_CODES,
    RUNTIME_MODELS_CODES,
    RUNTIME_TYPES_CODES,
)


def runtime_role_example_lines(
    *, runtime_root: str, active_codes: frozenset[str]
) -> tuple[str, ...]:
    """Return canonical examples only for roles established by active rules."""

    package: str = _module_path(runtime_root).rsplit(".", maxsplit=1)[-1]
    sections: list[str] = []
    if RUNTIME_MAIN_CODES.issubset(active_codes):
        sections.extend(_main_example(package=package))
    if RUNTIME_MODELS_CODES.issubset(active_codes):
        sections.extend(_models_example(frozen=RUNTIME_FROZEN_MODEL_CODES.issubset(active_codes)))
    if RUNTIME_HELPERS_CODES.issubset(active_codes):
        sections.extend(
            _helpers_example(detailed=RUNTIME_HELPERS_CONTENT_CODES.issubset(active_codes))
        )
    if RUNTIME_CLASSES_CODES.issubset(active_codes):
        sections.extend(_classes_example(package=package))
    if RUNTIME_TYPES_CODES.issubset(active_codes):
        sections.extend(_types_example())
    if RUNTIME_CONSTANTS_CODES.issubset(active_codes):
        sections.extend(_constants_example())
    if RUNTIME_EXCEPTIONS_CODES.issubset(active_codes):
        sections.extend(_exceptions_example())
    if not sections:
        return ()
    return ("### Role Examples", "", *sections)


def _main_example(*, package: str) -> tuple[str, ...]:
    return (
        "#### `main/read_invoice.py`",
        "",
        (
            "Expose exactly one public entry function and keep phase work in _helpers/. Use up to "
            "two private functions only when entry-specific glue is genuinely needed:"
        ),
        "",
        "```python",
        f"from {package}.invoices._helpers.loading import load_invoice",
        f"from {package}.invoices._helpers.normalization import normalize_invoice",
        f"from {package}.invoices.models import Invoice",
        "",
        "def read_invoice(invoice_id: str) -> Invoice:",
        "    loaded: Invoice = load_invoice(invoice_id)",
        "    return normalize_invoice(loaded)",
        "```",
        "",
    )


def _models_example(*, frozen: bool) -> tuple[str, ...]:
    decorator: str = "@dataclass(frozen=True, slots=True)" if frozen else "@dataclass(slots=True)"
    return (
        "#### `models.py`",
        "",
        "```python",
        "from dataclasses import dataclass",
        "",
        decorator,
        "class Invoice:",
        "    identifier: str",
        "    total_cents: int",
        "```",
        "",
        "When Pydantic is already in use, its structured models belong in the same role:",
        "",
        "```python",
        "from pydantic import BaseModel",
        "",
        "class InvoiceQuery(BaseModel):",
        "    customer_id: str",
        "    include_paid: bool = False",
        "```",
        "",
    )


def _helpers_example(*, detailed: bool) -> tuple[str, ...]:
    if not detailed:
        return (
            "#### `_helpers/normalization.py`",
            "",
            "```python",
            "def normalize_total(total_cents: int) -> int:",
            "    return max(total_cents, 0)",
            "```",
            "",
        )
    return (
        "#### `_helpers/normalization.py`",
        "",
        "Private constants and support dataclasses precede helper functions:",
        "",
        "```python",
        "from dataclasses import dataclass",
        "",
        '_DEFAULT_CURRENCY: str = "USD"',
        "",
        "@dataclass(frozen=True, slots=True)",
        "class _NormalizedAmount:",
        "    cents: int",
        "    currency: str",
        "",
        "def normalize_amount(cents: int) -> _NormalizedAmount:",
        "    return _NormalizedAmount(cents=max(cents, 0), currency=_DEFAULT_CURRENCY)",
        "```",
        "",
    )


def _classes_example(*, package: str) -> tuple[str, ...]:
    return (
        "#### `classes/invoice_repository.py`",
        "",
        "Each module under `classes/` defines exactly one top-level class:",
        "",
        "```python",
        f"from {package}.invoices.models import Invoice",
        "",
        "class InvoiceRepository:",
        "    def __init__(self, invoices: dict[str, Invoice]) -> None:",
        "        self._invoices = invoices",
        "",
        "    def read(self, invoice_id: str) -> Invoice:",
        "        return self._invoices[invoice_id]",
        "```",
        "",
    )


def _types_example() -> tuple[str, ...]:
    return (
        "#### `types.py`",
        "",
        "```python",
        "from enum import StrEnum",
        "from typing import NewType, TypeAlias",
        "",
        'InvoiceId = NewType("InvoiceId", str)',
        "InvoiceLine: TypeAlias = tuple[str, int]",
        "",
        "class InvoiceState(StrEnum):",
        '    DRAFT = "draft"',
        '    PAID = "paid"',
        "```",
        "",
    )


def _constants_example() -> tuple[str, ...]:
    return (
        "#### `constants.py`",
        "",
        "```python",
        "DEFAULT_PAGE_SIZE: int = 100",
        "MAX_RETRY_ATTEMPTS: int = 3",
        "```",
        "",
    )


def _exceptions_example() -> tuple[str, ...]:
    return (
        "#### `exceptions.py`",
        "",
        "```python",
        "class InvoiceNotFoundError(LookupError):",
        '    """Raised when an invoice identifier is unknown."""',
        "```",
        "",
    )


def _module_path(path: str) -> str:
    return path.strip("/").replace("/", ".")
