"""Render only repository structures proven by active core rules and config."""

from __future__ import annotations

import json
from collections.abc import Mapping

from strata.agentdocs._helpers.role_examples import runtime_role_example_lines
from strata.agentdocs.constants import (
    RUNTIME_BASIC_CODES,
    RUNTIME_CLASSES_CODES,
    RUNTIME_CONSTANTS_CODES,
    RUNTIME_ENTRY_CODES,
    RUNTIME_EXCEPTIONS_CODES,
    RUNTIME_HELPERS_CODES,
    RUNTIME_MAIN_CODES,
    RUNTIME_MODELS_CODES,
    RUNTIME_NESTED_CODES,
    RUNTIME_PACKAGE_NAMING_CODES,
    RUNTIME_TYPES_CODES,
    TEST_AUTHORING_CODES,
    TEST_BASIC_CODES,
    TEST_CASE_FILE_CODES,
    TEST_RUNTIME_MIRROR_CODES,
    TEST_TOOLING_MIRROR_CODES,
    THRESHOLD_RULE_CODES,
    TOOLING_ADAPTER_CODES,
    TOOLING_PACKAGE_CODES,
    TOOLING_RULES_CODES,
)
from strata.config.models import Config, ThresholdOverride
from strata.discovery.constants import HELPERS_DIRECTORY_NAME
from strata.discovery.types import RoleName
from strata.rules.authoring.types import Threshold
from strata.rules.roles.types import RoleCode


def repository_guidance_lines(
    *, config: Config, active_codes: frozenset[str], project_prefix: str = ""
) -> tuple[str, ...]:
    """Return structure guidance supported by the active rule evidence."""

    sections: list[str] = []
    sections.extend(
        _runtime_guidance(
            config=config,
            active_codes=active_codes,
            project_prefix=project_prefix,
        )
    )
    sections.extend(
        _test_guidance(
            config=config,
            active_codes=active_codes,
            project_prefix=project_prefix,
        )
    )
    sections.extend(
        _tooling_guidance(
            config=config,
            active_codes=active_codes,
            project_prefix=project_prefix,
        )
    )
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


def memory_retrieval_guidance_lines(config: Config) -> tuple[str, ...]:
    """Return staged retrieval guidance only for enabled repository memory."""

    if not config.experimental.memory:
        return ()
    return (
        "## Strata Memory Retrieval",
        "",
        (
            "Use Strata Memory for durable repository knowledge; keep transient reasoning and "
            "scratch state outside memory. Tasks track committed work, notes provide lookup "
            "context, decisions preserve durable choices, and skills are instructions to follow."
        ),
        "",
        (
            "Before creating a task, query existing active tasks to avoid duplicates. Inspect "
            "`memory.blocked_tasks`, report blockers, and preserve authorized out-of-order work."
        ),
        "",
        (
            "After each coherent verified chunk, update the active task ledger or checklist. Mark "
            "only complete work, leave partial work unchecked with its gaps, and reconcile claims "
            "against the implementation and tests."
        ),
        "",
        "Retrieve in stages:",
        "",
        "1. Query document titles and section headings first.",
        "2. Retrieve relevant sections second.",
        "3. Use `strata memory graph <document-or-pattern>` for relationship context third.",
        "4. Read full documents only when focused retrieval is insufficient.",
        "",
        (
            "If current views are insufficient, search archived documents for history and "
            "regressions. Treat skills as instructions and notes as lookup context."
        ),
        "",
        "Useful schema and staged-query examples:",
        "",
        "```bash",
        "strata memory schema current_documents",
        'strata memory sql "SELECT identity, title, artifact_kind FROM '
        'memory.current_documents ORDER BY title"',
        'strata memory sql "SELECT document_identity, heading_text, heading_path FROM '
        'memory.sections ORDER BY document_identity, ordinal"',
        'strata memory sql "SELECT document_identity, heading_text, raw_markdown FROM '
        "memory.sections WHERE document_identity = 'task:...' ORDER BY ordinal\"",
        'strata memory sql "SELECT identity, title FROM memory.blocked_tasks ORDER BY identity"',
        'strata memory sql "SELECT identity, title FROM memory.documents WHERE '
        "archive_state = 'archived' ORDER BY identity\"",
        "```",
        "",
    )


def configured_threshold_override_lines(
    *, config: Config, active_codes: frozenset[str]
) -> tuple[str, ...]:
    """Render configured overrides whenever at least one active rule can consult them."""

    applicable: list[ThresholdOverride] = []
    for override in config.threshold_overrides:
        if any(THRESHOLD_RULE_CODES[threshold] & active_codes for threshold in override.thresholds):
            applicable.append(override)
    applicable_overrides: tuple[ThresholdOverride, ...] = tuple(applicable)
    if not applicable_overrides:
        return ()
    return (
        "## Configured Threshold Overrides",
        "",
        *_threshold_override_lines(overrides=applicable_overrides),
    )


def _runtime_guidance(
    *, config: Config, active_codes: frozenset[str], project_prefix: str
) -> tuple[str, ...]:
    if not RUNTIME_BASIC_CODES.issubset(active_codes):
        return ()
    nested_enabled: bool = RUNTIME_NESTED_CODES.issubset(active_codes)
    entries: tuple[str, ...] = _runtime_role_entries(active_codes=active_codes)
    lines: list[str] = ["### Runtime", ""]
    for configured_root in config.roots:
        root: str = _display_path(path=configured_root, prefix=project_prefix)
        if nested_enabled:
            lines.extend(("Leaf domain:", ""))
        lines.extend(("```text", f"{root}/", "└── <domain>/"))
        if not nested_enabled:
            lines.extend(("```", ""))
            continue
        lines.extend(_tree_entries(entries=entries, indent="    "))
        lines.extend(("```", "", "Branch domain:", "", "```text", f"{root}/", "└── <domain>/"))
        lines.append("    └── <subdomain>/")
        lines.extend(_tree_entries(entries=entries, indent="        "))
        lines.extend(("```", ""))
    lines.extend(_domain_shape_lines(active_codes=active_codes))
    lines.extend(_container_guidance(config=config, active_codes=active_codes))
    if not nested_enabled:
        return tuple(lines)
    lines.extend(
        runtime_role_example_lines(
            runtime_root=_display_path(path=config.roots[0]),
            active_codes=active_codes,
        )
    )
    return tuple(lines)


def _runtime_role_entries(*, active_codes: frozenset[str]) -> tuple[str, ...]:
    main_entries: tuple[str, ...] = (
        ("main/",)
        if RUNTIME_MAIN_CODES.issubset(active_codes) or RoleCode.LEAF_MAIN_BOUNDARY in active_codes
        else ()
    )
    return (
        *main_entries,
        *_entry_when(label="_helpers/", evidence=RUNTIME_HELPERS_CODES, active=active_codes),
        *_entry_when(label="classes/", evidence=RUNTIME_CLASSES_CODES, active=active_codes),
        *_entry_when(label="models.py", evidence=RUNTIME_MODELS_CODES, active=active_codes),
        *_entry_when(label="types.py", evidence=RUNTIME_TYPES_CODES, active=active_codes),
        *_entry_when(label="constants.py", evidence=RUNTIME_CONSTANTS_CODES, active=active_codes),
        *_entry_when(label="exceptions.py", evidence=RUNTIME_EXCEPTIONS_CODES, active=active_codes),
    )


def _domain_shape_lines(*, active_codes: frozenset[str]) -> tuple[str, ...]:
    lines: list[str] = [
        "### Domain Shape",
        "",
        (
            "Domains may be leaves with role content directly beneath `<domain>/`, or branches "
            "containing named subdomains. Do not mix the two shapes."
        ),
        "",
        (
            "For a singleton capability, prefer a leaf instead of creating a placeholder "
            "`core` subdomain."
        ),
        "",
        "Promote a leaf to a branch only when multiple real capabilities exist.",
        "",
    ]
    if RoleCode.LEAF_MAIN_BOUNDARY in active_codes:
        lines.extend(
            (
                (
                    "Every leaf domain or subdomain must contain a direct `main/` boundary with "
                    "at least one non-`__init__.py` Python entry module. Branch-domain parents do "
                    "not need their own `main/`; their leaf subdomains do."
                ),
                "",
                (
                    "Do not add placeholder `main/` packages. If a package owns only passive "
                    "models, types, constants, exceptions, or classes, move them into the closest "
                    "domain or subdomain whose `main/` behavior owns and uses them."
                ),
                "",
            )
        )
    if RUNTIME_PACKAGE_NAMING_CODES.issubset(active_codes):
        lines.extend(
            (
                (
                    "Generic package names are banned, including `base`, `common`, `lib`, "
                    "`misc`, `shared`, `util`, and `utils`. Name the business domain or "
                    "technical capability owner instead."
                ),
                "",
            )
        )
    return tuple(lines)


def _container_guidance(*, config: Config, active_codes: frozenset[str]) -> tuple[str, ...]:
    enabled_roles: tuple[RoleName, ...] = tuple(
        role
        for role, code in (
            (RoleName.HELPERS, RoleCode.HELPERS_PACKAGE_LAYOUT),
            (RoleName.MAIN, RoleCode.MAIN_PACKAGE_LAYOUT),
        )
        if code in active_codes
    )
    if not enabled_roles:
        return ()
    lines: list[str] = ["### Role Containers", ""]
    for role in enabled_roles:
        threshold: Threshold = (
            Threshold.MAX_HELPERS_CONTAINER_MODULES
            if role is RoleName.HELPERS
            else Threshold.MAX_MAIN_CONTAINER_MODULES
        )
        role_thresholds: Mapping[Threshold, int] | None = config.role_thresholds.get(role.value)
        limit: int = (
            role_thresholds[threshold]
            if role_thresholds is not None and threshold in role_thresholds
            else config.thresholds[threshold]
        )
        lines.extend(_role_container_lines(role=role, limit=limit))
    lines.extend(
        (
            (
                "Every container holds direct Python modules or Python-containing buckets, never "
                "both. Empty and asset-only directories do not count as buckets."
            ),
            "",
            (
                "Configured base `max_role_depth` is "
                f"{config.thresholds[Threshold.MAX_ROLE_DEPTH]}. "
                "Role tables and matching path overrides can provide the effective per-path value."
            ),
            "",
            (
                "Runtime role names are banned as buckets: `main`, `_helpers`, `classes`, "
                "`models`, `types`, `constants`, and `exceptions`."
            ),
            "",
        )
    )
    if RoleCode.BANNED_GENERIC_PACKAGE_NAME in active_codes:
        lines.extend(
            (
                "Generic bucket names remain SFR204 concerns and do not receive a second "
                "container-layout fault.",
                "",
            )
        )
    if RoleCode.HELPERS_RESERVED_ROLE_FILENAMES in active_codes:
        lines.extend(
            (
                (
                    "Fixed role filenames such as `models.py`, `types.py`, `constants.py`, and "
                    "`exceptions.py` are sibling roles and must never be nested beneath "
                    "`_helpers/`."
                ),
                "",
            )
        )
    if RoleName.MAIN in enabled_roles and RUNTIME_ENTRY_CODES.issubset(active_codes):
        lines.extend(
            (
                (
                    "Every non-`__init__.py` module whose first structural role is `main` is an "
                    "entry module, including grouped main modules. Entry shape and container depth "
                    "are orthogonal, so an over-depth main path may independently receive both "
                    "layout and entry-shape diagnostics. A `main` bucket below another role is not "
                    "an entry boundary."
                ),
                "",
            )
        )
    return tuple(lines)


def _role_container_lines(*, role: RoleName, limit: int) -> tuple[str, ...]:
    noun: str = "helper" if role is RoleName.HELPERS else "entry"
    path_name: str = HELPERS_DIRECTORY_NAME if role is RoleName.HELPERS else role
    return (
        f"#### `{path_name}/`: Flat Or Grouped",
        "",
        (
            f"Each `{path_name}/` container has an effective module limit; "
            f"its configured role base is {limit}."
        ),
        "",
        "```text",
        f"{path_name}/",
        f"├── first_{noun}.py",
        f"└── second_{noun}.py",
        "```",
        "",
        "or group every module:",
        "",
        "```text",
        f"{path_name}/",
        "├── reading/",
        f"│   └── read_{noun}.py",
        "└── writing/",
        f"    └── write_{noun}.py",
        "```",
        "",
    )


def _threshold_override_lines(*, overrides: tuple[ThresholdOverride, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    lines.extend(
        (
            (
                "Patterns match reported repository paths. Specificity is compared as "
                "`(literal segments, literal characters, -globstars, -wildcards, declaration "
                "order)`; the greatest tuple wins. Literal segments contain no `*`, literal "
                "characters exclude `/` and `*`, globstars count `**` segments, and wildcards "
                "count remaining `*` tokens."
            ),
            "",
            "```toml",
        )
    )
    for override in overrides:
        paths: str = ", ".join(json.dumps(path) for path in sorted(override.paths))
        thresholds: str = ", ".join(
            f"{threshold.value} = {value}"
            for threshold, value in sorted(
                override.thresholds.items(), key=lambda item: item[0].value
            )
        )
        lines.extend(
            (
                "[[threshold_overrides]]",
                f"paths = [{paths}]",
                f"reason = {json.dumps(override.reason)}",
                f"thresholds = {{ {thresholds} }}",
                "",
            )
        )
    lines.extend(("```", ""))
    return tuple(lines)


def _test_guidance(
    *, config: Config, active_codes: frozenset[str], project_prefix: str
) -> tuple[str, ...]:
    if not config.tests or not TEST_BASIC_CODES.issubset(active_codes):
        return ()
    runtime_mirrors_enabled: bool = TEST_RUNTIME_MIRROR_CODES.issubset(active_codes)
    entries: tuple[str, ...] = (
        ("_test_types.py", "test_feature.py") if TEST_CASE_FILE_CODES.issubset(active_codes) else ()
    )
    lines: list[str] = ["### Tests", ""]
    for configured_test_root in config.tests:
        test_root: str = _display_path(path=configured_test_root, prefix=project_prefix)
        if not runtime_mirrors_enabled:
            lines.extend(
                (
                    "```text",
                    f"{test_root}/",
                    "└── <scope>/",
                    "    └── <mirrored-root>/...",
                    "```",
                    "",
                )
            )
            continue
        for configured_runtime_root in config.roots:
            runtime_root: str = _display_path(
                path=configured_runtime_root,
                prefix=project_prefix,
            )
            lines.extend(
                (
                    "```text",
                    f"{test_root}/",
                    "└── <scope>/",
                    f"    └── {runtime_root}/<domain>[/<subdomain>]/",
                )
            )
            lines.extend(_tree_entries(entries=entries, indent="        "))
            lines.extend(("```", ""))
    if not runtime_mirrors_enabled:
        return tuple(lines)
    if config.tooling and TEST_TOOLING_MIRROR_CODES.issubset(active_codes):
        for configured_test_root in config.tests:
            for configured_tooling_root in config.tooling:
                lines.extend(
                    (
                        "Tooling-backed tests mirror under "
                        f"`{_display_path(path=configured_test_root, prefix=project_prefix)}"
                        "/<scope>/"
                        f"{_display_path(path=configured_tooling_root, prefix=project_prefix)}"
                        "/<area>/`.",
                        "",
                    )
                )
    if TEST_AUTHORING_CODES.issubset(active_codes) and RUNTIME_MAIN_CODES.issubset(active_codes):
        lines.extend(
            _test_authoring_example(
                runtime_root=_display_path(path=config.roots[0]),
                test_root=_display_path(path=config.tests[0]),
            )
        )
    return tuple(lines)


def _test_authoring_example(*, runtime_root: str, test_root: str) -> tuple[str, ...]:
    runtime_package: str = _module_path(runtime_root).rsplit(".", maxsplit=1)[-1]
    test_case_module: str = (
        f"{_module_path(test_root)}.unit.{_module_path(runtime_root)}.invoices._test_types"
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
        f"from {runtime_package}.invoices.main.read_invoice import read_invoice",
        f"from {runtime_package}.invoices.models import Invoice",
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


def _tooling_guidance(
    *, config: Config, active_codes: frozenset[str], project_prefix: str
) -> tuple[str, ...]:
    if not config.tooling:
        return ()
    adapter_enabled: bool = TOOLING_ADAPTER_CODES.issubset(active_codes)
    package_enabled: bool = TOOLING_PACKAGE_CODES.issubset(active_codes)
    if not adapter_enabled and not package_enabled:
        return ()
    entries: list[str] = []
    if adapter_enabled:
        entries.append("run_tool.py")
    if package_enabled:
        entries.append("<tool>/")
    role_entries: tuple[str, ...] = (
        *_entry_when(label="main/", evidence=RUNTIME_MAIN_CODES, active=active_codes),
        *_entry_when(label="_helpers/", evidence=RUNTIME_HELPERS_CODES, active=active_codes),
        *_entry_when(label="classes/", evidence=RUNTIME_CLASSES_CODES, active=active_codes),
        *_entry_when(label="rules/", evidence=TOOLING_RULES_CODES, active=active_codes),
    )
    lines: list[str] = ["### Tooling", ""]
    for configured_tooling_root in config.tooling:
        lines.extend(
            (
                "```text",
                f"{_display_path(path=configured_tooling_root, prefix=project_prefix)}/",
            )
        )
        lines.extend(_tree_entries(entries=tuple(entries), indent=""))
        if package_enabled:
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


def _display_path(*, path: str, prefix: str = "") -> str:
    display: str = path.rstrip("/") or "."
    return f"{prefix}/{display}" if prefix else display


def _module_path(path: str) -> str:
    return path.strip("/").replace("/", ".")
