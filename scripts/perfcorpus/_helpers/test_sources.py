"""Render one domain's mirrored test files for the generated corpus."""

from __future__ import annotations

from types import MappingProxyType

from scripts.perfcorpus._helpers.naming import class_prefix
from scripts.perfcorpus.constants import (
    PACKAGE_NAME,
    RECORD_STATES,
    SOURCE_ROOT,
    TEST_SCOPE,
    TESTS_ROOT,
)
from scripts.perfcorpus.models import RenderedFiles

_TEST_INIT_CONTENT: str = '"""Generated corpus test package."""\n'


def render_domain_tests(*, domain: str) -> RenderedFiles:
    """Return one domain's convention-following mirrored test files."""

    base: str = f"{TESTS_ROOT}/{TEST_SCOPE}/{SOURCE_ROOT}/{PACKAGE_NAME}/{domain}"
    prefix: str = class_prefix(domain=domain)
    files: dict[str, str] = {
        f"{base}/__init__.py": _TEST_INIT_CONTENT,
        f"{base}/_test_types.py": _test_types_module(domain=domain, prefix=prefix),
        f"{base}/test_read_{domain}.py": _read_test_module(domain=domain, prefix=prefix),
        f"{base}/test_export_{domain}.py": _export_test_module(domain=domain, prefix=prefix),
        f"{base}/test_audit_{domain}.py": _audit_test_module(domain=domain, prefix=prefix),
    }
    return RenderedFiles(files=MappingProxyType(files), faults=0)


def _types_import_path(*, domain: str) -> str:
    return f"{TESTS_ROOT}.{TEST_SCOPE}.{SOURCE_ROOT}.{PACKAGE_NAME}.{domain}"


def _test_types_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Test-case types for {domain} behavior."""\n'
        "\n"
        "from dataclasses import dataclass\n"
        "\n"
        "\n"
        "@dataclass(frozen=True)\n"
        f"class Read{prefix}TestCase:\n"
        f'    """One {domain} read behavior case."""\n'
        "\n"
        "    description: str\n"
        "    identifier: str\n"
        "    expected_identifier: str\n"
        "\n"
        "\n"
        "@dataclass(frozen=True)\n"
        f"class Export{prefix}TestCase:\n"
        f'    """One {domain} export behavior case."""\n'
        "\n"
        "    description: str\n"
        "    identifiers: tuple[str, ...]\n"
        "    expected_record_count: int\n"
        "\n"
        "\n"
        "@dataclass(frozen=True)\n"
        f"class Audit{prefix}TestCase:\n"
        f'    """One {domain} audit behavior case."""\n'
        "\n"
        "    description: str\n"
        "    totals: tuple[int, ...]\n"
        "    expected_total_cents: int\n"
    )


def _read_test_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Behavior tests for the {domain} read entry."""\n'
        "\n"
        "import pytest\n"
        "\n"
        f"from {PACKAGE_NAME}.{domain}.main.read_{domain} import read_{domain}\n"
        f"from {PACKAGE_NAME}.{domain}.models import {prefix}Record\n"
        f"from {_types_import_path(domain=domain)}._test_types import Read{prefix}TestCase\n"
        "\n"
        "\n"
        "@pytest.mark.parametrize(\n"
        '    "test_case",\n'
        "    [\n"
        f"        Read{prefix}TestCase(\n"
        '            description="returns the requested record",\n'
        '            identifier="record-1",\n'
        '            expected_identifier="record-1",\n'
        "        ),\n"
        f"        Read{prefix}TestCase(\n"
        '            description="preserves the requested identifier",\n'
        '            identifier="record-2",\n'
        '            expected_identifier="record-2",\n'
        "        ),\n"
        "    ],\n"
        "    ids=lambda case: case.description,\n"
        ")\n"
        "def test_given_identifier_when_reading_then_returns_expected_record(\n"
        f"    test_case: Read{prefix}TestCase,\n"
        ") -> None:\n"
        f"    result: {prefix}Record = read_{domain}(identifier=test_case.identifier)\n"
        "\n"
        "    assert result.identifier == test_case.expected_identifier\n"
        + _read_state_tests(domain=domain, prefix=prefix)
    )


def _read_state_tests(*, domain: str, prefix: str) -> str:
    sections: list[str] = []
    for state in RECORD_STATES:
        sections.append(
            "\n"
            "\n"
            "@pytest.mark.parametrize(\n"
            '    "test_case",\n'
            "    [\n"
            f"        Read{prefix}TestCase(\n"
            f'            description="returns the {state} record",\n'
            f'            identifier="{state}-record-1",\n'
            f'            expected_identifier="{state}-record-1",\n'
            "        ),\n"
            f"        Read{prefix}TestCase(\n"
            f'            description="preserves the {state} identifier",\n'
            f'            identifier="{state}-record-2",\n'
            f'            expected_identifier="{state}-record-2",\n'
            "        ),\n"
            "    ],\n"
            "    ids=lambda case: case.description,\n"
            ")\n"
            f"def test_given_{state}_identifier_when_reading_then_returns_expected_record(\n"
            f"    test_case: Read{prefix}TestCase,\n"
            ") -> None:\n"
            f"    result: {prefix}Record = read_{domain}(identifier=test_case.identifier)\n"
            "\n"
            "    assert result.identifier == test_case.expected_identifier\n"
        )
    return "".join(sections)


def _export_test_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Behavior tests for the {domain} export entry."""\n'
        "\n"
        "import pytest\n"
        "\n"
        f"from {PACKAGE_NAME}.{domain}.main.export_{domain} import export_{domain}\n"
        f"from {PACKAGE_NAME}.{domain}.models import {prefix}Batch\n"
        f"from {_types_import_path(domain=domain)}._test_types import Export{prefix}TestCase\n"
        "\n"
        "\n"
        "@pytest.mark.parametrize(\n"
        '    "test_case",\n'
        "    [\n"
        f"        Export{prefix}TestCase(\n"
        '            description="exports one record per identifier",\n'
        '            identifiers=("record-1", "record-2"),\n'
        "            expected_record_count=2,\n"
        "        ),\n"
        f"        Export{prefix}TestCase(\n"
        '            description="exports nothing for no identifiers",\n'
        "            identifiers=(),\n"
        "            expected_record_count=0,\n"
        "        ),\n"
        "    ],\n"
        "    ids=lambda case: case.description,\n"
        ")\n"
        "def test_given_identifiers_when_exporting_then_returns_expected_batch(\n"
        f"    test_case: Export{prefix}TestCase,\n"
        ") -> None:\n"
        f"    result: {prefix}Batch = export_{domain}(identifiers=test_case.identifiers)\n"
        "\n"
        "    assert len(result.records) == test_case.expected_record_count\n"
        + _export_state_tests(domain=domain, prefix=prefix)
    )


def _export_state_tests(*, domain: str, prefix: str) -> str:
    sections: list[str] = []
    for state in RECORD_STATES:
        sections.append(
            "\n"
            "\n"
            "@pytest.mark.parametrize(\n"
            '    "test_case",\n'
            "    [\n"
            f"        Export{prefix}TestCase(\n"
            f'            description="exports the {state} identifiers",\n'
            f'            identifiers=("{state}-1", "{state}-2"),\n'
            "            expected_record_count=2,\n"
            "        ),\n"
            f"        Export{prefix}TestCase(\n"
            f'            description="exports one {state} identifier",\n'
            f'            identifiers=("{state}-1",),\n'
            "            expected_record_count=1,\n"
            "        ),\n"
            "    ],\n"
            "    ids=lambda case: case.description,\n"
            ")\n"
            f"def test_given_{state}_identifiers_when_exporting_then_returns_expected_batch(\n"
            f"    test_case: Export{prefix}TestCase,\n"
            ") -> None:\n"
            f"    result: {prefix}Batch = export_{domain}(identifiers=test_case.identifiers)\n"
            "\n"
            "    assert len(result.records) == test_case.expected_record_count\n"
        )
    return "".join(sections)


def _audit_test_module(*, domain: str, prefix: str) -> str:
    return (
        f'"""Behavior tests for the {domain} audit entry."""\n'
        "\n"
        "import pytest\n"
        "\n"
        f"from {PACKAGE_NAME}.{domain}._helpers.record_shaping import shape_record\n"
        f"from {PACKAGE_NAME}.{domain}.main.audit_{domain} import audit_{domain}\n"
        f"from {PACKAGE_NAME}.{domain}.models import {prefix}Record, {prefix}Summary\n"
        f"from {_types_import_path(domain=domain)}._test_types import Audit{prefix}TestCase\n"
        "\n"
        "\n"
        "@pytest.mark.parametrize(\n"
        '    "test_case",\n'
        "    [\n"
        f"        Audit{prefix}TestCase(\n"
        '            description="sums bounded totals",\n'
        "            totals=(10, 20),\n"
        "            expected_total_cents=30,\n"
        "        ),\n"
        f"        Audit{prefix}TestCase(\n"
        '            description="sums nothing for no records",\n'
        "            totals=(),\n"
        "            expected_total_cents=0,\n"
        "        ),\n"
        "    ],\n"
        "    ids=lambda case: case.description,\n"
        ")\n"
        "def test_given_records_when_auditing_then_returns_expected_summary(\n"
        f"    test_case: Audit{prefix}TestCase,\n"
        ") -> None:\n"
        f"    records: tuple[{prefix}Record, ...] = tuple(\n"
        f'        shape_record(identifier=f"record-{{index}}", total_cents=total)\n'
        "        for index, total in enumerate(test_case.totals)\n"
        "    )\n"
        "\n"
        f"    result: {prefix}Summary = audit_{domain}(records=records)\n"
        "\n"
        "    assert result.total_cents == test_case.expected_total_cents\n"
        + _audit_state_tests(domain=domain, prefix=prefix)
    )


def _audit_state_tests(*, domain: str, prefix: str) -> str:
    sections: list[str] = []
    for state in RECORD_STATES:
        sections.append(
            "\n"
            "\n"
            "@pytest.mark.parametrize(\n"
            '    "test_case",\n'
            "    [\n"
            f"        Audit{prefix}TestCase(\n"
            f'            description="sums bounded {state} totals",\n'
            "            totals=(10, 20, 30),\n"
            "            expected_total_cents=60,\n"
            "        ),\n"
            f"        Audit{prefix}TestCase(\n"
            f'            description="sums no {state} totals",\n'
            "            totals=(),\n"
            "            expected_total_cents=0,\n"
            "        ),\n"
            "    ],\n"
            "    ids=lambda case: case.description,\n"
            ")\n"
            f"def test_given_{state}_records_when_auditing_then_returns_expected_summary(\n"
            f"    test_case: Audit{prefix}TestCase,\n"
            ") -> None:\n"
            f"    records: tuple[{prefix}Record, ...] = tuple(\n"
            f'        shape_record(identifier=f"{state}-{{index}}", total_cents=total)\n'
            "        for index, total in enumerate(test_case.totals)\n"
            "    )\n"
            "\n"
            f"    result: {prefix}Summary = audit_{domain}(records=records)\n"
            "\n"
            "    assert result.total_cents == test_case.expected_total_cents\n"
        )
    return "".join(sections)
