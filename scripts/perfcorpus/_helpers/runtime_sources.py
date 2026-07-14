"""Render one domain's runtime source files for the generated corpus."""

from __future__ import annotations

from types import MappingProxyType

from scripts.perfcorpus._helpers.naming import class_prefix
from scripts.perfcorpus.constants import (
    HELPER_MODULE_NAMES,
    PACKAGE_NAME,
    RECORD_STATES,
    SOURCE_ROOT,
)
from scripts.perfcorpus.models import RenderedFiles

_INIT_CONTENT: str = '"""Generated corpus package."""\n'


def render_runtime_domain(
    *,
    domain: str,
    dependency: str,
    helper_offset: int,
    annotation_fault_every: int,
    magic_fault_every: int,
) -> RenderedFiles:
    """Return one leaf domain's runtime files with deterministic fault injection."""

    base: str = f"{SOURCE_ROOT}/{PACKAGE_NAME}/{domain}"
    prefix: str = class_prefix(domain=domain)
    files: dict[str, str] = {
        f"{base}/__init__.py": _INIT_CONTENT,
        f"{base}/models.py": _models_module(domain=domain, prefix=prefix),
        f"{base}/types.py": _types_module(domain=domain, prefix=prefix),
        f"{base}/constants.py": _constants_module(domain=domain),
        f"{base}/exceptions.py": _exceptions_module(domain=domain, prefix=prefix),
        f"{base}/classes/__init__.py": _INIT_CONTENT,
        f"{base}/classes/record_store.py": _store_module(domain=domain, prefix=prefix),
        f"{base}/main/__init__.py": _INIT_CONTENT,
        f"{base}/main/read_{domain}.py": _read_entry_module(domain=domain, prefix=prefix),
        f"{base}/main/export_{domain}.py": _export_entry_module(domain=domain, prefix=prefix),
        f"{base}/main/audit_{domain}.py": _audit_entry_module(domain=domain, prefix=prefix),
        f"{base}/_helpers/__init__.py": _INIT_CONTENT,
    }
    faults: int = 0
    for position, helper_name in enumerate(HELPER_MODULE_NAMES):
        helper_index: int = helper_offset + position
        drop_annotation: bool = helper_index % annotation_fault_every == 0
        magic_comparison: bool = helper_index % magic_fault_every == 0
        files[f"{base}/_helpers/{helper_name}.py"] = _helper_module(
            domain=domain,
            dependency=dependency,
            prefix=prefix,
            helper_name=helper_name,
            drop_annotation=drop_annotation,
            magic_comparison=magic_comparison,
        )
        faults += int(drop_annotation) + int(magic_comparison)
    return RenderedFiles(files=MappingProxyType(files), faults=faults)


def _models_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Structured records for the {domain} domain."""\n'
        "\n"
        "from dataclasses import dataclass\n"
        "\n"
        "\n"
        "@dataclass(frozen=True, slots=True)\n"
        f"class {prefix}Record:\n"
        f'    """One {domain} record."""\n'
        "\n"
        "    identifier: str\n"
        "    total_cents: int\n"
        "    entry_count: int\n"
        "    settled: bool\n"
        "\n"
        "\n"
        "@dataclass(frozen=True, slots=True)\n"
        f"class {prefix}Batch:\n"
        f'    """One ordered {domain} record batch."""\n'
        "\n"
        f"    records: tuple[{prefix}Record, ...]\n"
        "    batch_total_cents: int\n"
        "\n"
        "\n"
        "@dataclass(frozen=True, slots=True)\n"
        f"class {prefix}Summary:\n"
        f'    """Aggregated {domain} totals."""\n'
        "\n"
        "    record_count: int\n"
        "    settled_count: int\n"
        "    total_cents: int\n"
    )


def _types_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Type declarations for the {domain} domain."""\n'
        "\n"
        "from enum import StrEnum\n"
        "\n"
        "\n"
        f"class {prefix}State(StrEnum):\n"
        f'    """Lifecycle states for {domain} records."""\n'
        "\n"
        '    DRAFT = "draft"\n'
        '    PENDING = "pending"\n'
        '    SETTLED = "settled"\n'
        '    ARCHIVED = "archived"\n'
    )


def _constants_module(*, domain: str) -> str:
    return (
        f'"""Constants for the {domain} domain."""\n'
        "\n"
        "DEFAULT_BATCH_SIZE: int = 25\n"
        "MAX_TOTAL_CENTS: int = 250\n"
        "MIN_ENTRY_COUNT: int = 1\n"
        "SETTLEMENT_THRESHOLD_CENTS: int = 100\n"
    )


def _exceptions_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Exceptions for the {domain} domain."""\n'
        "\n"
        "\n"
        f"class {prefix}NotFoundError(LookupError):\n"
        f'    """Raised when a {domain} record is unknown."""\n'
        "\n"
        "\n"
        f"class {prefix}InvalidTotalError(ValueError):\n"
        f'    """Raised when a {domain} total is out of range."""\n'
    )


def _store_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Record storage for the {domain} domain."""\n'
        "\n"
        f"from {PACKAGE_NAME}.{domain}.exceptions import {prefix}NotFoundError\n"
        f"from {PACKAGE_NAME}.{domain}.models import {prefix}Record\n"
        "\n"
        "\n"
        f"class {prefix}Store:\n"
        f'    """Store {domain} records in memory."""\n'
        "\n"
        f"    def __init__(self, *, records: dict[str, {prefix}Record]) -> None:\n"
        '        """Index records by identifier."""\n'
        "\n"
        f"        self._records: dict[str, {prefix}Record] = records\n"
        "\n"
        f"    def read(self, *, identifier: str) -> {prefix}Record:\n"
        '        """Return one stored record."""\n'
        "\n"
        f"        record: {prefix}Record | None = self._records.get(identifier)\n"
        "        if record is None:\n"
        f"            raise {prefix}NotFoundError(identifier)\n"
        "        return record\n"
        "\n"
        f"    def upsert(self, *, record: {prefix}Record) -> {prefix}Record:\n"
        '        """Store one record and return it."""\n'
        "\n"
        "        self._records[record.identifier] = record\n"
        "        return record\n"
        "\n"
        "    def discard(self, *, identifier: str) -> bool:\n"
        '        """Remove one record and report whether it existed."""\n'
        "\n"
        "        existed: bool = identifier in self._records\n"
        "        self._records.pop(identifier, None)\n"
        "        return existed\n"
        "\n"
        f"    def identifiers(self) -> tuple[str, ...]:\n"
        '        """Return deterministic stored identifiers."""\n'
        "\n"
        "        return tuple(sorted(self._records))\n"
        "\n"
        "    def count(self) -> int:\n"
        '        """Return how many records are stored."""\n'
        "\n"
        "        return len(self._records)\n" + _store_state_methods(prefix=prefix)
    )


def _store_state_methods(*, prefix: str) -> str:
    sections: list[str] = []
    for state in RECORD_STATES:
        sections.append(
            "\n"
            f"    def {state}_records(self) -> tuple[{prefix}Record, ...]:\n"
            f'        """Return deterministic records for the {state} bucket."""\n'
            "\n"
            f"        selected: list[{prefix}Record] = []\n"
            "        for identifier in sorted(self._records):\n"
            f"            record: {prefix}Record = self._records[identifier]\n"
            "            if record.settled:\n"
            "                selected.append(record)\n"
            "        return tuple(selected)\n"
            "\n"
            f"    def {state}_total_cents(self) -> int:\n"
            f'        """Return the combined total for the {state} bucket."""\n'
            "\n"
            "        total: int = 0\n"
            "        for record in self._records.values():\n"
            "            if record.settled:\n"
            "                total += record.total_cents\n"
            "        return total\n"
        )
    return "".join(sections)


def _read_entry_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Read entry for the {domain} domain."""\n'
        "\n"
        f"from {PACKAGE_NAME}.{domain}._helpers.{HELPER_MODULE_NAMES[0]} import shape_record\n"
        f"from {PACKAGE_NAME}.{domain}.models import {prefix}Record\n"
        "\n"
        "\n"
        f"def read_{domain}(*, identifier: str) -> {prefix}Record:\n"
        f'    """Return one shaped {domain} record."""\n'
        "\n"
        "    return shape_record(identifier=identifier, total_cents=100)\n"
    )


def _export_entry_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Export entry for the {domain} domain."""\n'
        "\n"
        f"from {PACKAGE_NAME}.{domain}._helpers.{HELPER_MODULE_NAMES[1]} import select_batch\n"
        f"from {PACKAGE_NAME}.{domain}.models import {prefix}Batch\n"
        "\n"
        "\n"
        f"def export_{domain}(*, identifiers: tuple[str, ...]) -> {prefix}Batch:\n"
        f'    """Return one exported {domain} batch."""\n'
        "\n"
        "    return select_batch(identifiers=identifiers)\n"
    )


def _audit_entry_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Audit entry for the {domain} domain."""\n'
        "\n"
        f"from {PACKAGE_NAME}.{domain}._helpers.{HELPER_MODULE_NAMES[2]} import summarize_records\n"
        f"from {PACKAGE_NAME}.{domain}.models import {prefix}Record, {prefix}Summary\n"
        "\n"
        "\n"
        f"def audit_{domain}(*, records: tuple[{prefix}Record, ...]) -> {prefix}Summary:\n"
        f'    """Return one audited {domain} summary."""\n'
        "\n"
        "    return summarize_records(records=records)\n"
    )


def _helper_module(
    *,
    domain: str,
    dependency: str,
    prefix: str,
    helper_name: str,
    drop_annotation: bool,
    magic_comparison: bool,
) -> str:
    heading: str = helper_name.replace("_", " ").capitalize()
    identifier_parameter: str = "identifier" if drop_annotation else "identifier: str"
    bound_expression: str = (
        "total_cents if total_cents > 250 else DEFAULT_BATCH_SIZE"
        if magic_comparison
        else "min(total_cents, MAX_TOTAL_CENTS)"
    )
    dependency_prefix: str = class_prefix(domain=dependency)
    return (
        f'"""{heading} helpers for the {domain} domain."""\n'
        "\n"
        f"from {PACKAGE_NAME}.{dependency}.models import {dependency_prefix}Record\n"
        f"from {PACKAGE_NAME}.{domain}.constants import (\n"
        "    DEFAULT_BATCH_SIZE,\n"
        "    MAX_TOTAL_CENTS,\n"
        "    MIN_ENTRY_COUNT,\n"
        "    SETTLEMENT_THRESHOLD_CENTS,\n"
        ")\n"
        f"from {PACKAGE_NAME}.{domain}.exceptions import {prefix}InvalidTotalError\n"
        f"from {PACKAGE_NAME}.{domain}.models import "
        f"{prefix}Batch, {prefix}Record, {prefix}Summary\n"
        "\n"
        "\n"
        f"def shape_record(*, {identifier_parameter}, total_cents: int) -> {prefix}Record:\n"
        f'    """Return one bounded {domain} record."""\n'
        "\n"
        f"    bounded: int = {bound_expression}\n"
        "    settled: bool = bounded >= SETTLEMENT_THRESHOLD_CENTS\n"
        f"    return {prefix}Record(\n"
        "        identifier=identifier,\n"
        "        total_cents=bounded,\n"
        "        entry_count=MIN_ENTRY_COUNT,\n"
        "        settled=settled,\n"
        "    )\n"
        "\n"
        "\n"
        f"def select_batch(*, identifiers: tuple[str, ...]) -> {prefix}Batch:\n"
        f'    """Return one ordered {domain} batch for the identifiers."""\n'
        "\n"
        f"    records: list[{prefix}Record] = []\n"
        "    for identifier in sorted(identifiers):\n"
        f"        record: {prefix}Record = shape_record(\n"
        "            identifier=identifier,\n"
        "            total_cents=DEFAULT_BATCH_SIZE,\n"
        "        )\n"
        "        records.append(record)\n"
        "    batch_total: int = sum(record.total_cents for record in records)\n"
        f"    return {prefix}Batch(records=tuple(records), batch_total_cents=batch_total)\n"
        "\n"
        "\n"
        f"def summarize_records(*, records: tuple[{prefix}Record, ...]) -> {prefix}Summary:\n"
        f'    """Return aggregated {domain} totals."""\n'
        "\n"
        "    settled_count: int = sum(1 for record in records if record.settled)\n"
        "    total_cents: int = sum(record.total_cents for record in records)\n"
        f"    return {prefix}Summary(\n"
        "        record_count=len(records),\n"
        "        settled_count=settled_count,\n"
        "        total_cents=total_cents,\n"
        "    )\n"
        "\n"
        "\n"
        f"def checked_record(*, record: {prefix}Record) -> {prefix}Record:\n"
        f'    """Return the record or raise on an invalid {domain} total."""\n'
        "\n"
        "    if record.total_cents > MAX_TOTAL_CENTS:\n"
        f"        raise {prefix}InvalidTotalError(record.identifier)\n"
        "    if record.entry_count < MIN_ENTRY_COUNT:\n"
        f"        raise {prefix}InvalidTotalError(record.identifier)\n"
        "    return record\n"
        "\n"
        "\n"
        f"def merge_totals(*, record: {prefix}Record, other: {dependency_prefix}Record) -> int:\n"
        '    """Return combined totals across domains."""\n'
        "\n"
        "    return record.total_cents + other.total_cents\n"
        "\n"
        "\n"
        f"def settled_identifiers(*, records: tuple[{prefix}Record, ...]) -> tuple[str, ...]:\n"
        f'    """Return deterministic settled {domain} identifiers."""\n'
        "\n"
        "    selected: list[str] = []\n"
        "    for record in records:\n"
        "        if record.settled:\n"
        "            selected.append(record.identifier)\n"
        "    return tuple(sorted(selected))\n"
        "\n"
        "\n"
        f"def ranked_records(\n"
        f"    *, records: tuple[{prefix}Record, ...]\n"
        f") -> tuple[{prefix}Record, ...]:\n"
        f'    """Return {domain} records ordered by descending total."""\n'
        "\n"
        f"    ordered: list[{prefix}Record] = sorted(\n"
        "        records,\n"
        "        key=lambda record: (-record.total_cents, record.identifier),\n"
        "    )\n"
        "    return tuple(ordered)\n"
        "\n"
        "\n"
        f"def pending_batch(*, records: tuple[{prefix}Record, ...]) -> {prefix}Batch:\n"
        f'    """Return the unsettled {domain} records as one batch."""\n'
        "\n"
        f"    pending: list[{prefix}Record] = []\n"
        "    for record in records:\n"
        "        if not record.settled:\n"
        "            pending.append(record)\n"
        "    batch_total: int = sum(record.total_cents for record in pending)\n"
        f"    return {prefix}Batch(records=tuple(pending), batch_total_cents=batch_total)\n"
        + _helper_state_functions(domain=domain, prefix=prefix)
    )


def _helper_state_functions(*, domain: str, prefix: str) -> str:
    sections: list[str] = []
    for state in RECORD_STATES:
        sections.append(
            "\n"
            "\n"
            f"def {state}_batch(\n"
            "    *,\n"
            f"    records: tuple[{prefix}Record, ...],\n"
            "    limit_cents: int,\n"
            f") -> {prefix}Batch:\n"
            f'    """Return the bounded {state} bucket for the {domain} domain."""\n'
            "\n"
            f"    selected: list[{prefix}Record] = []\n"
            "    for record in records:\n"
            "        if record.total_cents <= limit_cents:\n"
            "            selected.append(record)\n"
            "    total: int = sum(record.total_cents for record in selected)\n"
            f"    return {prefix}Batch(records=tuple(selected), batch_total_cents=total)\n"
            "\n"
            "\n"
            f"def {state}_summary(\n"
            "    *,\n"
            f"    records: tuple[{prefix}Record, ...],\n"
            "    minimum_cents: int,\n"
            f") -> {prefix}Summary:\n"
            f'    """Return aggregated {state} totals for the {domain} domain."""\n'
            "\n"
            "    settled_count: int = 0\n"
            "    total_cents: int = 0\n"
            "    for record in records:\n"
            "        if record.total_cents >= minimum_cents:\n"
            "            settled_count += int(record.settled)\n"
            "            total_cents += record.total_cents\n"
            f"    return {prefix}Summary(\n"
            "        record_count=len(records),\n"
            "        settled_count=settled_count,\n"
            "        total_cents=total_cents,\n"
            "    )\n"
        )
    return "".join(sections)
