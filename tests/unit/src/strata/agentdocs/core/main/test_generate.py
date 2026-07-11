"""Tests for evidence-based repository guidance generation."""

from __future__ import annotations

import pytest

from strata.agentdocs.core.main.generate import generate_skill
from strata.config.core.models import Config, RuleExceptionEntry
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.constants import CORE_RULES
from tests.unit.src.strata.agentdocs.core.main._test_types import GuidanceTestCase
from tests.unit.src.strata.agentdocs.core.main.helpers import (
    core_rule_codes_for_prefix,
    core_rules_for_codes,
    structure_fragment_is_absent,
)


@pytest.mark.parametrize(
    "test_case",
    [
        GuidanceTestCase(
            description="active rule exceptions show exact symbols and review reason",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                rule_exceptions=(
                    RuleExceptionEntry(
                        rule="SFS120",
                        path="src/acme/external.py",
                        symbols=("Collector.update",),
                        reason="The external API invokes this method positionally.",
                    ),
                ),
            ),
            rule_codes=("SFS120",),
            expected_fragments=(
                "## Active Rule Exceptions",
                "`SFS120` in `src/acme/external.py`: `Collector.update`",
                "Reason: The external API invokes this method positionally.",
            ),
            expected_absent_fragments=("# noqa",),
        ),
        GuidanceTestCase(
            description="full core rules show detailed configured runtime tests and tooling",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=tuple(rule.code for rule in CORE_RULES),
            expected_fragments=(
                "## Repository Structure",
                "## Navigation And Work Handoffs",
                "run `strata map <symbol> --depth 4` before editing",
                "Rerun the same map after implementation",
                "Load this guidance before running any `strata` command",
                "primary benefit is helping the user understand the system",
                "Every displayed function must include its repository-relative path",
                "SOURCE-RESOLVED DYNAMIC BOUNDARY",
                "Default to the smallest affected branch",
                "Use a full before/after walkthrough only when ownership",
                "Do not force a graph into a handoff",
                "`DONE`, `PENDING`, and `WE ARE HERE` are agent-authored",
                "### Runtime",
                "src/acme/",
                "### Subdomain Naming",
                "Do not use `core` as the default subdomain name.",
                "cache/fingerprints/",
                "analysis/core/",
                "cache/core/",
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
                "Tooling-backed tests mirror under `tests/<scope>/scripts/<area>/`.",
                "### Tooling",
                "run_tool.py",
                "rules/",
            ),
            expected_absent_fragments=(),
        ),
        GuidanceTestCase(
            description="foundation rules show reduced runtime and test skeletons",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=("SFR306", "SFR307", "SFT001", "SFT002", "SFT003"),
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
            description="all configured layout roots appear in generated guidance",
            config=Config(
                roots=("python/mypkg", "lib/shared"),
                tests=("qa", "checks"),
                tooling=("dev/tools", "scripts"),
            ),
            rule_codes=tuple(rule.code for rule in CORE_RULES),
            expected_fragments=(
                "python/mypkg/",
                "lib/shared/",
                "qa/",
                "checks/",
                "qa/<scope>/dev/tools/<area>/",
                "checks/<scope>/scripts/<area>/",
                "dev/tools/",
                "scripts/",
            ),
            expected_absent_fragments=(),
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
                "SFT301",
                "SFT204",
                "SFT001",
                "SFT002",
                "SFT003",
                "SFT004",
                "SFT005",
                "SFT006",
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
            rule_codes=("SFR705", "SFT001", "SFT002", "SFT003"),
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
            expected_fragments=(
                "Use whenever Strata is mentioned or used",
                "## Navigation And Work Handoffs",
                "## Active Rules",
                "## SFX001: single-line-docstrings",
            ),
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

    assert all(fragment in document for fragment in test_case.expected_fragments)
    assert all(
        structure_fragment_is_absent(document=document, fragment=fragment)
        for fragment in test_case.expected_absent_fragments
    )
