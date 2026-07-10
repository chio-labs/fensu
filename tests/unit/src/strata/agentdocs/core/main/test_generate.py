"""Tests for evidence-based repository guidance generation."""

from __future__ import annotations

import pytest

from strata.agentdocs.core.main.generate import generate_skill
from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.constants import CORE_RULES
from tests.unit.src.strata.agentdocs.core.main._test_types import GuidanceTestCase
from tests.unit.src.strata.agentdocs.core.main.helpers import (
    core_rule_codes_for_prefix,
    core_rules_for_codes,
)


@pytest.mark.parametrize(
    "test_case",
    [
        GuidanceTestCase(
            description="full core rules show detailed configured runtime tests and tooling",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=tuple(rule.code for rule in CORE_RULES),
            expected_fragments=(
                "## Repository Structure",
                "### Runtime",
                "src/acme/",
                "models.py",
                "exceptions.py",
                "### Role Examples",
                "Expose exactly one public entry function and keep phase work in helpers.",
                "return normalize_invoice(loaded)",
                "@dataclass(frozen=True, slots=True)",
                "class InvoiceQuery(BaseModel):",
                "class _NormalizedAmount:",
                "class InvoiceRepository:",
                "InvoiceLine: TypeAlias = tuple[str, int]",
                "class InvoiceState(StrEnum):",
                "DEFAULT_PAGE_SIZE: int = 100",
                "class InvoiceNotFoundError(LookupError):",
                "### Tests",
                "src/acme/<domain>/<subdomain>/",
                "_test_types.py",
                "class ReadInvoiceTestCase:",
                "from acme.billing.invoices.main.read_invoice import read_invoice",
                "from tests.unit.src.acme.billing.invoices._test_types import ReadInvoiceTestCase",
                "Tooling-backed tests mirror under `tests/<scope>/scripts/<tool>/`.",
                "### Tooling",
                "run_tool.py",
                "rules/",
            ),
            expected_absent_fragments=(),
        ),
        GuidanceTestCase(
            description="foundation rules show reduced runtime and test skeletons",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=("SFR306", "SFR307", "SFT028", "SFT029", "SFT030"),
            expected_fragments=(
                "## Repository Structure",
                "### Runtime",
                "<subpackage>/",
                "### Tests",
                "<mirrored-root>/...",
            ),
            expected_absent_fragments=(
                "models.py",
                "_test_types.py",
                "class ReadInvoiceTestCase:",
                "### Tooling",
            ),
        ),
        GuidanceTestCase(
            description="model role without frozen-model rule shows a mutable dataclass declaration",
            config=Config(roots=("src/acme",), tests=(), tooling=()),
            rule_codes=("SFR001", "SFR101", "SFR304", "SFR305", "SFR306", "SFR307"),
            expected_fragments=("#### `models.py`", "@dataclass(slots=True)", "class Invoice:"),
            expected_absent_fragments=("@dataclass(frozen=True, slots=True)",),
        ),
        GuidanceTestCase(
            description="test layout without authoring evidence shows files but no code example",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=()),
            rule_codes=(
                "SFT006",
                "SFT026",
                "SFT028",
                "SFT029",
                "SFT030",
                "SFT031",
                "SFT032",
                "SFT033",
            ),
            expected_fragments=("### Tests", "_test_types.py", "test_feature.py"),
            expected_absent_fragments=("class ReadInvoiceTestCase:", "@pytest.mark.parametrize"),
        ),
        GuidanceTestCase(
            description="test authoring rules without main ownership omit a misleading runtime test",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=()),
            rule_codes=core_rule_codes_for_prefix("SFT"),
            expected_fragments=("### Tests", "_test_types.py", "test_feature.py"),
            expected_absent_fragments=("class ReadInvoiceTestCase:", "@pytest.mark.parametrize"),
        ),
        GuidanceTestCase(
            description="one proven runtime role appears without unsupported role claims",
            config=Config(roots=("src/acme",), tests=(), tooling=()),
            rule_codes=("SFR001", "SFR101", "SFR304", "SFR305", "SFR306", "SFR307"),
            expected_fragments=("### Runtime", "<subdomain>/", "models.py"),
            expected_absent_fragments=(
                "main/",
                "helpers/",
                "classes/",
                "types.py",
                "constants.py",
                "exceptions.py",
                "### Tests",
                "### Tooling",
            ),
        ),
        GuidanceTestCase(
            description="tool package rule alone shows only basic configured tooling",
            config=Config(roots=("src/acme",), tests=(), tooling=("tools",)),
            rule_codes=("SFR705",),
            expected_fragments=("## Repository Structure", "### Tooling", "tools/", "<tool>/"),
            expected_absent_fragments=("run_tool.py", "main/", "helpers/", "rules/"),
        ),
        GuidanceTestCase(
            description="disabled test and tooling scopes suppress otherwise active guidance",
            config=Config(roots=("src/acme",), tests=(), tooling=()),
            rule_codes=("SFR705", "SFT028", "SFT029", "SFT030"),
            expected_fragments=("## Active Rules",),
            expected_absent_fragments=(
                "## Repository Structure",
                "### Tests",
                "### Tooling",
            ),
        ),
        GuidanceTestCase(
            description="unrelated active rule omits unsupported repository examples",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=("SFX001",),
            expected_fragments=("## Active Rules", "## SFX001: single-line-docstrings"),
            expected_absent_fragments=(
                "## Repository Structure",
                "### Runtime",
                "### Tests",
                "### Tooling",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_config_and_active_rules_when_generating_then_shows_only_proven_guidance(
    test_case: GuidanceTestCase,
) -> None:
    rules: tuple[RuleSpec, ...] = core_rules_for_codes(test_case.rule_codes)

    document: str = generate_skill(config=test_case.config, rules=rules)
    guidance: str = document.partition("## Active Rules")[0]

    assert all(fragment in document for fragment in test_case.expected_fragments)
    assert all(fragment not in guidance for fragment in test_case.expected_absent_fragments)
