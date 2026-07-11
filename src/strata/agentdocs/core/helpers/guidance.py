"""Render only repository structures proven by active core rules and config."""

from __future__ import annotations

from strata.agentdocs.core.constants import (
    RUNTIME_BASIC_CODES,
    RUNTIME_CLASSES_CODES,
    RUNTIME_CONSTANTS_CODES,
    RUNTIME_EXCEPTIONS_CODES,
    RUNTIME_HELPERS_CODES,
    RUNTIME_MAIN_CODES,
    RUNTIME_MODELS_CODES,
    RUNTIME_NESTED_CODES,
    RUNTIME_TYPES_CODES,
    TEST_AUTHORING_CODES,
    TEST_BASIC_CODES,
    TEST_CASE_FILE_CODES,
    TEST_RUNTIME_MIRROR_CODES,
    TEST_TOOLING_MIRROR_CODES,
    TOOLING_ADAPTER_CODES,
    TOOLING_PACKAGE_CODES,
    TOOLING_RULES_CODES,
)
from strata.agentdocs.core.helpers.role_examples import runtime_role_example_lines
from strata.config.core.models import Config


def repository_guidance_lines(*, config: Config, active_codes: frozenset[str]) -> tuple[str, ...]:
    """Return structure guidance supported by the active rule evidence."""

    sections: list[str] = []
    sections.extend(_runtime_guidance(config=config, active_codes=active_codes))
    sections.extend(_test_guidance(config=config, active_codes=active_codes))
    sections.extend(_tooling_guidance(config=config, active_codes=active_codes))
    if not sections:
        return ()
    return (
        "## Repository Structure",
        "",
        (
            "Only structures established by this repository's active core rules are shown. "
            "Omitted structures are not implied."
        ),
        "",
        *sections,
    )


def _runtime_guidance(*, config: Config, active_codes: frozenset[str]) -> tuple[str, ...]:
    if not RUNTIME_BASIC_CODES.issubset(active_codes):
        return ()
    root: str = _display_path(config.roots[0])
    lines: list[str] = ["### Runtime", "", "```text", f"{root}/", "└── <domain>/"]
    if not RUNTIME_NESTED_CODES.issubset(active_codes):
        lines.extend(("    └── <subpackage>/", "```", ""))
        return tuple(lines)
    lines.append("    └── <subdomain>/")
    entries: tuple[str, ...] = _runtime_role_entries(active_codes=active_codes)
    lines.extend(_tree_entries(entries=entries, indent="        "))
    lines.extend(("```", ""))
    lines.extend(_subdomain_naming_lines())
    lines.extend(runtime_role_example_lines(runtime_root=root, active_codes=active_codes))
    return tuple(lines)


def _runtime_role_entries(*, active_codes: frozenset[str]) -> tuple[str, ...]:
    return (
        *_entry_when(label="main/", evidence=RUNTIME_MAIN_CODES, active=active_codes),
        *_entry_when(label="helpers/", evidence=RUNTIME_HELPERS_CODES, active=active_codes),
        *_entry_when(label="classes/", evidence=RUNTIME_CLASSES_CODES, active=active_codes),
        *_entry_when(label="models.py", evidence=RUNTIME_MODELS_CODES, active=active_codes),
        *_entry_when(label="types.py", evidence=RUNTIME_TYPES_CODES, active=active_codes),
        *_entry_when(label="constants.py", evidence=RUNTIME_CONSTANTS_CODES, active=active_codes),
        *_entry_when(label="exceptions.py", evidence=RUNTIME_EXCEPTIONS_CODES, active=active_codes),
    )


def _subdomain_naming_lines() -> tuple[str, ...]:
    return (
        "### Subdomain Naming",
        "",
        (
            "Do not use `core` as the default subdomain name. Prefer a capability-specific "
            "owner when the package already has a stable purpose or independent lifecycle."
        ),
        "",
        (
            "Use `core` only for one cohesive central engine where a narrower name would be "
            "artificial. Avoid speculative package splitting before boundaries are real."
        ),
        "",
        "```text",
        "Prefer:",
        "cache/fingerprints/",
        "cache/storage/",
        "cache/invalidation/",
        "",
        "Potentially valid:",
        "analysis/core/",
        "evaluation/core/",
        "",
        "Avoid when distinct capabilities are already known:",
        "cache/core/",
        "```",
        "",
    )


def _test_guidance(*, config: Config, active_codes: frozenset[str]) -> tuple[str, ...]:
    if not config.tests or not TEST_BASIC_CODES.issubset(active_codes):
        return ()
    test_root: str = _display_path(config.tests[0])
    lines: list[str] = ["### Tests", "", "```text", f"{test_root}/", "└── <scope>/"]
    if not TEST_RUNTIME_MIRROR_CODES.issubset(active_codes):
        lines.extend(("    └── <mirrored-root>/...", "```", ""))
        return tuple(lines)
    runtime_root: str = _display_path(config.roots[0])
    lines.append(f"    └── {runtime_root}/<domain>/<subdomain>/")
    entries: tuple[str, ...] = (
        ("_test_types.py", "test_feature.py") if TEST_CASE_FILE_CODES.issubset(active_codes) else ()
    )
    lines.extend(_tree_entries(entries=entries, indent="        "))
    lines.extend(("```", ""))
    if config.tooling and TEST_TOOLING_MIRROR_CODES.issubset(active_codes):
        tooling_root: str = _display_path(config.tooling[0])
        lines.extend(
            (
                f"Tooling-backed tests mirror under `{test_root}/<scope>/{tooling_root}/<tool>/`.",
                "",
            )
        )
    if TEST_AUTHORING_CODES.issubset(active_codes) and RUNTIME_MAIN_CODES.issubset(active_codes):
        lines.extend(_test_authoring_example(runtime_root=runtime_root, test_root=test_root))
    return tuple(lines)


def _test_authoring_example(*, runtime_root: str, test_root: str) -> tuple[str, ...]:
    runtime_package: str = _module_path(runtime_root).rsplit(".", maxsplit=1)[-1]
    test_case_module: str = (
        f"{_module_path(test_root)}.unit.{_module_path(runtime_root)}.billing.invoices._test_types"
    )
    return (
        "`_test_types.py`:",
        "",
        "```python",
        "from dataclasses import dataclass",
        "",
        "@dataclass(frozen=True)",
        "class ReadInvoiceTestCase:",
        "    description: str",
        "    invoice_id: str",
        "    expected_identifier: str",
        "```",
        "",
        "`test_feature.py`:",
        "",
        "```python",
        "import pytest",
        "",
        f"from {runtime_package}.billing.invoices.main.read_invoice import read_invoice",
        f"from {runtime_package}.billing.invoices.models import Invoice",
        f"from {test_case_module} import ReadInvoiceTestCase",
        "",
        "@pytest.mark.parametrize(",
        '    "test_case",',
        "    [",
        "        ReadInvoiceTestCase(",
        '            description="returns the requested invoice",',
        '            invoice_id="invoice-1",',
        '            expected_identifier="invoice-1",',
        "        )",
        "    ],",
        "    ids=lambda case: case.description,",
        ")",
        "def test_given_invoice_id_when_reading_invoice_then_returns_expected_invoice(",
        "    test_case: ReadInvoiceTestCase,",
        ") -> None:",
        "    result: Invoice = read_invoice(test_case.invoice_id)",
        "",
        "    assert result.identifier == test_case.expected_identifier",
        "```",
        "",
    )


def _tooling_guidance(*, config: Config, active_codes: frozenset[str]) -> tuple[str, ...]:
    if not config.tooling:
        return ()
    adapter_enabled: bool = TOOLING_ADAPTER_CODES.issubset(active_codes)
    package_enabled: bool = TOOLING_PACKAGE_CODES.issubset(active_codes)
    if not adapter_enabled and not package_enabled:
        return ()
    tooling_root: str = _display_path(config.tooling[0])
    entries: list[str] = []
    if adapter_enabled:
        entries.append("run_tool.py")
    if package_enabled:
        entries.append("<tool>/")
    lines: list[str] = ["### Tooling", "", "```text", f"{tooling_root}/"]
    lines.extend(_tree_entries(entries=tuple(entries), indent=""))
    if package_enabled:
        role_entries: tuple[str, ...] = (
            *_entry_when(label="main/", evidence=RUNTIME_MAIN_CODES, active=active_codes),
            *_entry_when(label="helpers/", evidence=RUNTIME_HELPERS_CODES, active=active_codes),
            *_entry_when(label="classes/", evidence=RUNTIME_CLASSES_CODES, active=active_codes),
            *_entry_when(label="rules/", evidence=TOOLING_RULES_CODES, active=active_codes),
        )
        lines.extend(_tree_entries(entries=role_entries, indent="    "))
    lines.extend(("```", ""))
    return tuple(lines)


def _entry_when(*, label: str, evidence: frozenset[str], active: frozenset[str]) -> tuple[str, ...]:
    return (label,) if evidence.issubset(active) else ()


def _tree_entries(*, entries: tuple[str, ...], indent: str) -> tuple[str, ...]:
    rendered: list[str] = []
    for index, entry in enumerate(entries):
        connector: str = "└── " if index == len(entries) - 1 else "├── "
        rendered.append(f"{indent}{connector}{entry}")
    return tuple(rendered)


def _display_path(path: str) -> str:
    return path.rstrip("/") or "."


def _module_path(path: str) -> str:
    return path.strip("/").replace("/", ".")
