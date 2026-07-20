"""Tests for evidence-based repository guidance generation."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from fensu.agentdocs._helpers.authoring import authoring_lookup_lines, rule_context_lines
from fensu.agentdocs._helpers.guidance import (
    memory_retrieval_guidance_lines,
    repository_guidance_lines,
)
from fensu.agentdocs._helpers.ownership import skill_input_fingerprint
from fensu.agentdocs._helpers.work_practices import (
    custom_rule_authority_lines,
    work_practice_lines,
)
from fensu.agentdocs._helpers.workflow import navigation_workflow_lines
from fensu.agentdocs.main._generate import generate_skill
from fensu.config.models import (
    Config,
    ExperimentalConfig,
    MemoryConfig,
    MemoryTasksConfig,
    RuleExceptionEntry,
    ThresholdOverride,
)
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Threshold
from fensu.rules.catalog.constants import CORE_RULES
from tests.unit.src.fensu.agentdocs.main._test_types import (
    GuidanceTestCase,
    NativeInvariantAssetTestCase,
    SkillContentTestCase,
    SkillContextImmutabilityTestCase,
    SkillDeterminismTestCase,
)
from tests.unit.src.fensu.agentdocs.main.helpers import (
    comprehensive_generation_context,
    core_only_generation_context,
    core_rule_codes_for_prefix,
    core_rules_for_codes,
    custom_default_cache_generation_context,
    generation_context,
    mutate_generation_context,
    structure_fragment_is_absent,
)

_ESCAPED_OVERRIDE_PATH: str = 'src/"quoted"/back\\slash\n/**/*.py'
_ESCAPED_OVERRIDE_REASON: str = 'Generated "API" path.\nKeep \\ escapes.'


@pytest.mark.parametrize(
    "test_case",
    [
        NativeInvariantAssetTestCase(
            description="compiled native invariant sections match the current Python renderer",
            expected_section_count=8,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_invariant_asset_when_comparing_python_sections_then_bytes_match_worktree(
    test_case: NativeInvariantAssetTestCase,
) -> None:
    repository: Path = Path(__file__).resolve().parents[6]
    asset: dict[str, list[str]] = json.loads(
        (repository / "crates/fensu-cli/assets/skills_invariant.json").read_text(encoding="utf-8")
    )
    active_codes: frozenset[str] = frozenset(rule.code for rule in CORE_RULES)
    base_config: Config = Config(roots=("__ROOT__",), tests=("__TEST__",), tooling=())
    tooling_config: Config = Config(roots=("__ROOT__",), tests=("__TEST__",), tooling=("__TOOL__",))
    memory_config: Config = Config(
        roots=("__ROOT__",),
        experimental=ExperimentalConfig(memory=True),
        memory=MemoryConfig(tasks=MemoryTasksConfig(archive_after_days=987654321)),
    )
    expected: dict[str, list[str]] = {
        "authoring_lookup": list(authoring_lookup_lines()),
        "custom_authority": list(custom_rule_authority_lines()),
        "memory": list(memory_retrieval_guidance_lines(memory_config)),
        "navigation": list(navigation_workflow_lines()),
        "repository": list(
            repository_guidance_lines(config=base_config, active_codes=active_codes)
        ),
        "repository_tooling": list(
            repository_guidance_lines(config=tooling_config, active_codes=active_codes)
        ),
        "rule_context": list(rule_context_lines()),
        "work_practices": list(work_practice_lines()),
    }

    assert len(asset) == test_case.expected_section_count
    assert asset == expected


@pytest.mark.parametrize(
    "test_case",
    [
        GuidanceTestCase(
            description="disabled memory omits retrieval guidance without changing base policy",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                experimental=ExperimentalConfig(memory=False),
            ),
            rule_codes=("FFH001",),
            expected_fragments=("## Commands", "## Navigation And Work Handoffs"),
            expected_absent_fragments=(
                "## Fensu Memory Retrieval",
                "## Fensu Memory Operations",
                "## Phased Implementation",
                ".ai/tasks/",
                "memory.blocked_tasks",
            ),
        ),
        GuidanceTestCase(
            description="enabled memory adds concise staged retrieval and ledger guidance",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                experimental=ExperimentalConfig(memory=True),
            ),
            rule_codes=("FFH001",),
            expected_fragments=(
                "## Fensu Memory Retrieval",
                "durable repository knowledge",
                "transient reasoning and scratch state outside memory",
                "Tasks track committed work",
                "notes provide lookup context",
                "decisions preserve durable choices",
                "skills are instructions to follow",
                "query existing active tasks to avoid duplicates",
                "`memory.blocked_tasks`",
                "report blockers",
                "preserve authorized out-of-order work",
                "After each coherent verified chunk",
                "leave partial work unchecked with its gaps",
                "reconcile claims against the implementation and tests",
                "Query document titles and section headings first",
                "Retrieve relevant sections second",
                "fensu memory graph <document-or-pattern>",
                "Read full documents only",
                "search archived documents for history and regressions",
                "fensu memory schema current_documents",
                "FROM memory.sections",
                "## Fensu Memory Operations",
                "canonical Markdown under `.ai/` as authoritative",
                "tasks/{not-started,in-progress,completed,cancelled,superseded}/",
                "knowledge/repo/{notes,decisions,skills}/",
                "<YYYYMMDDTHHMMSS_ffffffZ>__<CATEGORY>-<kebab-slug>.md",
                "`SPIKE`, `FIX`, `PERF`, `FEAT`, `REFACTOR`, or `CHORE`",
                "SELECT identity, filesystem_path FROM memory.current_documents",
                "move the unchanged file between live lifecycle directories",
                "do not assume `git mv` applies",
                ".ai/tasks/not-started/",
                "fensu memory sync",
                "fensu memory check",
                "fensu memory archive",
                "never move documents into `.ai/_archive/` manually",
                "configured `7`-day retention",
                "## Phased Implementation",
                "vertical slices",
                "Leave partial work unchecked and record its gap",
                "observable end-to-end outcomes",
                "## Phase 1: Native Memory Check",
                "call the native engine, render exact faults",
                "command-parity and process-accounting coverage",
                "process trace contains no Python executable",
                "Separate phases such as `Add models`, `Add helpers`, and `Wire CLI`",
                "horizontal work queues and are not acceptable slices",
                "paired A/B measurements",
            ),
            expected_absent_fragments=("MCP", "corpus injection", "fensu memory locate"),
        ),
        GuidanceTestCase(
            description="selected naming behavior excludes unselected naming guidance",
            config=Config(roots=("src/acme",), tests=(), tooling=()),
            rule_codes=("FFN002",),
            expected_fragments=(
                "### FFN002: predicate-must-return-bool",
                "Return bool (or TypeGuard/TypeIs)",
            ),
            expected_absent_fragments=(
                "### FFN001:",
                "### FFN003:",
                "### FFN004:",
            ),
        ),
        GuidanceTestCase(
            description="active rule exceptions show exact symbols and review reason",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                rule_exceptions=(
                    RuleExceptionEntry(
                        rule="FFS120",
                        path="src/acme/external.py",
                        symbols=("Collector.update",),
                        reason="The external API invokes this method positionally.",
                    ),
                ),
            ),
            rule_codes=("FFS120",),
            expected_fragments=(
                "### Configured Rule Exceptions",
                'Rule "FFS120"; path="src/acme/external.py"; scope=["Collector.update"]',
                'reason="The external API invokes this method positionally."',
            ),
            expected_absent_fragments=("# noqa",),
        ),
        GuidanceTestCase(
            description="file level exception is explicit in generated guidance",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                rule_exceptions=(
                    RuleExceptionEntry(
                        rule="FFR307",
                        path="src/acme/domain/special.py",
                        reason="This file is an intentional adapter.",
                    ),
                ),
            ),
            rule_codes=("FFR307",),
            expected_fragments=(
                "### Configured Rule Exceptions",
                'Rule "FFR307"; path="src/acme/domain/special.py"; scope="file-level"',
                'reason="This file is an intentional adapter."',
            ),
            expected_absent_fragments=("symbols = []",),
        ),
        GuidanceTestCase(
            description="full core rules show detailed configured runtime tests and tooling",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=tuple(rule.code for rule in CORE_RULES),
            expected_fragments=(
                "## Repository Structure",
                "## Navigation And Work Handoffs",
                "run `fensu map <symbol> --depth 4` before editing",
                "Rerun the same map after implementation",
                "Load this guidance before running any `fensu` command",
                "primary benefit is helping the user understand the system",
                "Every displayed function must include its repository-relative path",
                "SOURCE-RESOLVED DYNAMIC BOUNDARY",
                "Default to the smallest affected branch",
                "Use a full before/after walkthrough only when ownership",
                "Do not force a graph into a handoff",
                "`DONE`, `PENDING`, and `WE ARE HERE` are agent-authored",
                "### Runtime",
                "src/acme/",
                "### Domain Shape",
                "Domains may be leaves",
                "Do not mix the two shapes.",
                "prefer a leaf instead of creating a placeholder `core` subdomain",
                "Promote a leaf to a branch only when multiple real capabilities exist.",
                "Generic package names are banned",
                "`misc`, `shared`, `util`, and `utils`",
                "Leaf domain:",
                "Branch domain:",
                "models.py",
                "exceptions.py",
                "### Role Examples",
                "### Role Containers",
                "#### `_helpers/`: Flat Or Grouped",
                "configured role base is 10",
                "#### `main/`: Flat Or Grouped",
                "configured role base is 20",
                "Configured base `max_role_depth` is 1",
                "Runtime role names are banned as buckets",
                "Generic bucket names remain FFR204 concerns",
                "Every non-`__init__.py` module whose first structural role is `main`",
                "Entry shape and container depth are orthogonal",
                "Expose exactly one public entry function and keep phase work in _helpers/.",
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
                "src/acme/<domain>[/<subdomain>]/",
                "_test_types.py",
                "class ReadInvoiceTestCase:",
                "from acme.invoices.main.read_invoice import read_invoice",
                "from tests.unit.src.acme.invoices._test_types import ReadInvoiceTestCase",
                "Tooling-backed tests mirror under `tests/<scope>/scripts/<area>/`.",
                "### Tooling",
                "run_tool.py",
                "rules/",
            ),
            expected_absent_fragments=(
                "Never use `core`",
                "main/ packages must remain flat orchestration surfaces",
                "Keep entry modules directly under main/",
            ),
        ),
        GuidanceTestCase(
            description="configured threshold override appears with exact precedence syntax",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                threshold_overrides=(
                    ThresholdOverride(
                        paths=("src/acme/**/main/commands/*.py",),
                        thresholds={Threshold.MAX_MAIN_CONTAINER_MODULES: 36},
                        reason="Product-width command surface.",
                    ),
                ),
            ),
            rule_codes=("FFR204", "FFR301", "FFR302", "FFR306", "FFR307", "FFR401"),
            expected_fragments=(
                "### Role Containers",
                "or group every module:",
                "Every container holds direct Python modules or Python-containing buckets",
                "Empty and asset-only directories do not count as buckets.",
                "## Configured Threshold Overrides",
                "`(literal segments, literal characters, -globstars, -wildcards, declaration order)`",
                "[[threshold_overrides]]",
                'paths = ["src/acme/**/main/commands/*.py"]',
                'reason = "Product-width command surface."',
                "thresholds = { max_main_container_modules = 36 }",
                "A `main` bucket below another role is not an entry boundary.",
            ),
            expected_absent_fragments=(
                "main/ packages must remain flat orchestration surfaces",
                "Keep entry modules directly under main/",
            ),
        ),
        GuidanceTestCase(
            description="unrelated annotation rule omits configured threshold override",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                threshold_overrides=(
                    ThresholdOverride(
                        paths=(_ESCAPED_OVERRIDE_PATH,),
                        thresholds={Threshold.MAX_FILE_LINES: 3000},
                        reason=_ESCAPED_OVERRIDE_REASON,
                    ),
                ),
            ),
            rule_codes=("FFA101",),
            expected_fragments=("## Blocking Rules",),
            expected_absent_fragments=(
                "## Configured Threshold Overrides",
                "[[threshold_overrides]]",
                "### Role Containers",
                "## Repository Structure",
            ),
        ),
        GuidanceTestCase(
            description="container file line and shape rules show applicable overrides only",
            config=Config(
                roots=("src/acme",),
                tests=(),
                tooling=(),
                threshold_overrides=(
                    ThresholdOverride(
                        paths=("src/acme/**/_helpers/*.py",),
                        thresholds={Threshold.MAX_HELPERS_CONTAINER_MODULES: 12},
                        reason="Container width.",
                    ),
                    ThresholdOverride(
                        paths=(_ESCAPED_OVERRIDE_PATH,),
                        thresholds={Threshold.MAX_FILE_LINES: 3000},
                        reason=_ESCAPED_OVERRIDE_REASON,
                    ),
                    ThresholdOverride(
                        paths=("src/acme/**/*.py",),
                        thresholds={Threshold.MAX_ARGUMENTS: 15},
                        reason="Generated signatures.",
                    ),
                    ThresholdOverride(
                        paths=("src/acme/**/*.py",),
                        thresholds={Threshold.MAX_MAIN_CONTAINER_MODULES: 30},
                        reason="Inactive main width.",
                    ),
                ),
            ),
            rule_codes=("FFR301", "FFR601", "FFS010"),
            expected_fragments=(
                "## Configured Threshold Overrides",
                "thresholds = { max_helpers_container_modules = 12 }",
                f"paths = [{json.dumps(_ESCAPED_OVERRIDE_PATH)}]",
                f"reason = {json.dumps(_ESCAPED_OVERRIDE_REASON)}",
                "thresholds = { max_file_lines = 3000 }",
                "thresholds = { max_arguments = 15 }",
            ),
            expected_absent_fragments=("Inactive main width.", "max_main_container_modules"),
        ),
        GuidanceTestCase(
            description="foundation rules show reduced runtime and test skeletons",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=("FFR306", "FFR307", "FFT001", "FFT002", "FFT003"),
            expected_fragments=(
                "## Repository Structure",
                "### Runtime",
                "### Domain Shape",
                "Domains may be leaves",
                "Do not mix the two shapes.",
                "prefer a leaf instead of creating a placeholder `core` subdomain",
                "### Tests",
                "<mirrored-root>/...",
            ),
            expected_absent_fragments=(
                "<subpackage>/",
                "models.py",
                "_test_types.py",
                "class ReadInvoiceTestCase:",
                "### Tooling",
                "Never use `core`",
            ),
        ),
        GuidanceTestCase(
            description="ownership rules require meaningful leaf entries and sibling role files",
            config=Config(roots=("src/acme",), tests=(), tooling=()),
            rule_codes=(
                "FFR301",
                "FFR302",
                "FFR303",
                "FFR304",
                "FFR305",
                "FFR306",
                "FFR307",
                "FFR309",
            ),
            expected_fragments=(
                "└── main/",
                "Every leaf domain or subdomain must contain a direct `main/` boundary",
                "Branch-domain parents do not need their own `main/`",
                "Do not add placeholder `main/` packages.",
                "move them into the closest domain or subdomain",
                "Fixed role filenames such as `models.py`, `types.py`, `constants.py`",
                "must never be nested beneath `_helpers/`",
            ),
            expected_absent_fragments=(),
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
            rule_codes=("FFR001", "FFR101", "FFR304", "FFR305", "FFR306", "FFR307"),
            expected_fragments=("#### `models.py`", "@dataclass(slots=True)", "class Invoice:"),
            expected_absent_fragments=("@dataclass(frozen=True, slots=True)",),
        ),
        GuidanceTestCase(
            description="test layout without authoring evidence shows files but no code example",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=()),
            rule_codes=(
                "FFT301",
                "FFT204",
                "FFT001",
                "FFT002",
                "FFT003",
                "FFT004",
                "FFT005",
                "FFT006",
            ),
            expected_fragments=("### Tests", "_test_types.py", "test_feature.py"),
            expected_absent_fragments=("class ReadInvoiceTestCase:", "@pytest.mark.parametrize"),
        ),
        GuidanceTestCase(
            description="test authoring rules without main ownership omit a misleading runtime test",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=()),
            rule_codes=core_rule_codes_for_prefix("FFT"),
            expected_fragments=("### Tests", "_test_types.py", "test_feature.py"),
            expected_absent_fragments=("class ReadInvoiceTestCase:", "@pytest.mark.parametrize"),
        ),
        GuidanceTestCase(
            description="one proven runtime role appears without unsupported role claims",
            config=Config(roots=("src/acme",), tests=(), tooling=()),
            rule_codes=("FFR001", "FFR101", "FFR304", "FFR305", "FFR306", "FFR307"),
            expected_fragments=(
                "### Runtime",
                "Leaf domain:",
                "src/acme/\n└── <domain>/\n    └── models.py",
                "Branch domain:",
                "src/acme/\n└── <domain>/\n    └── <subdomain>/\n        └── models.py",
                "### Domain Shape",
            ),
            expected_absent_fragments=(
                "main/",
                "_helpers/",
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
            rule_codes=("FFR705",),
            expected_fragments=("## Repository Structure", "### Tooling", "tools/", "<tool>/"),
            expected_absent_fragments=("run_tool.py", "main/", "_helpers/", "rules/"),
        ),
        GuidanceTestCase(
            description="disabled test and tooling scopes suppress otherwise active guidance",
            config=Config(roots=("src/acme",), tests=(), tooling=()),
            rule_codes=("FFR705", "FFT001", "FFT002", "FFT003"),
            expected_fragments=("## Blocking Rules",),
            expected_absent_fragments=(
                "## Repository Structure",
                "### Tests",
                "### Tooling",
            ),
        ),
        GuidanceTestCase(
            description="unrelated active rule omits unsupported repository examples",
            config=Config(roots=("src/acme",), tests=("tests",), tooling=("scripts",)),
            rule_codes=("FFH001",),
            expected_fragments=(
                "Use when modifying the project project governed by fensu.toml",
                "## Navigation And Work Handoffs",
                "## Blocking Rules",
                "### FFH001: single-line-docstrings",
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

    document: str = generate_skill(
        context=generation_context(config=test_case.config, blocking_rules=rules)
    )

    assert all(fragment in document for fragment in test_case.expected_fragments)
    assert all(
        structure_fragment_is_absent(document=document, fragment=fragment)
        for fragment in test_case.expected_absent_fragments
    )


@pytest.mark.parametrize(
    "test_case",
    [
        SkillContentTestCase(
            description="complete policy context renders mandatory project-specific guidance",
            context=comprehensive_generation_context(),
            expected_fragments=(
                'name: "fensu-project"',
                "## Working With Existing Drift",
                "architectural baseline, not authorization",
                "zero faults, treat that broader target as authorized scope",
                "fix the code under the current policy",
                "## Testing Refactors Safely",
                "PostgreSQL, Redis, Kafka or Redpanda",
                "`docker info`",
                "`podman info`",
                "SQLite as evidence for PostgreSQL-specific SQL",
                "deterministic race-oriented tests",
                "barriers, events, controlled workers, or transactional locks",
                "rather than relying on sleeps",
                "## Test Execution And Isolation",
                "pytest -n auto",
                "unique temporary paths, databases, schemas, ports, and resource names",
                "A sequential pass does not make the problem acceptable",
                "## Custom Rule Authority",
                "explicitly requested it or explicitly approved your proposal",
                "Do not ask for a redundant second confirmation",
                "## Effective Project Configuration",
                '`[tool.fensu]` in "pyproject.toml"',
                '- Current skill identity: "fensu-project"',
                "- Complete loaded catalogue size: 4",
                '- Product roots: ["lib/pkg", "src/\\"quoted\\""]',
                '- Blocking selectors (`select`): ["FFN", "XAC001"]',
                '- Warning selectors (`warn`): ["FFR706"]',
                '- Ignore selectors (`ignore`): ["FFH001"]',
                '- Blocking rule codes: ["FFN001", "XAC001"]',
                '- Warning rule codes: ["FFR706"]',
                '- Ignored matched rule codes: ["FFH001"]',
                '- `rule_paths`: ["scripts/fensu/rules/client_ownership.py", '
                '"scripts/other_rules"]',
                '- `rule_modules`: ["acme.more_policy", "acme.policy"]',
                "- Cache enabled: `true`",
                "- Cache requires cacheable rules: `true`",
                '- Evaluation include boundaries: ["lib/**/*.py", "src/**/*.py"]',
                '- Evaluation exclude boundaries: ["src/generated/**"]',
                "### Effective Global Thresholds",
                "- `max_arguments` = 10",
                'Role "helpers": `max_helpers_container_modules` = 14',
                'Role "main": `max_main_container_modules` = 24',
                "Declaration 1: paths=",
                '"max_distinct_calls": 18',
                'reason="Focused orchestration."',
                "### Effective Naming Contracts",
                '- "fetch_*" = "returns-value"',
                '- "is_*" = "returns-bool"',
                "### Configured Rule Exceptions",
                'Rule "FFN001"; path="lib/pkg/legacy.py"',
                'Rule "XAC001"; path="src/\\"quoted\\"/client.py"',
                "External `API` contract.\\nReviewed.",
                "## Warning Policy",
                "warning-only findings do not fail the command",
                "## RuleContext Public API",
                "The five public analysis zones",
                "`ctx.facts`",
                "`ctx.text`",
                "`ctx.syntax`",
                "`ctx.relations`",
                "`ctx.project`",
                "analysis(requester=ctx.path, path=path)",
                "dataclasses(requester=ctx.path, path=path)",
                "directory_entries(requester=ctx.path, path=path)",
                "module_function(requester=ctx.path, module_name=name, function_name=name)",
                "python_anchor(requester=ctx.path, path=path)",
                "exists(requester=ctx.path, path=path)",
                "is_dir(requester=ctx.path, path=path)",
                "is_file(requester=ctx.path, path=path)",
                "glob(requester=ctx.path, path=path, pattern=pattern, recursive=False)",
                "dependencies_for(requester=ctx.path)",
                "Position and ownership helpers",
                "AST helpers",
                "Fault constructors",
                "## Approved Custom Rule Authoring Lookup",
                "locate the active installation through `fensu.__file__`",
                "Only import authoring APIs from top-level `fensu`",
                "## Testing Custom Rules",
                "The effective minimum is `1` statically declared `RuleCase` value(s)",
                "including rules not selected for blocking or warning evaluation",
                "Verify cold and warm cache behavior",
                "from fensu import RuleCase, RuleResult, evaluate_rule",
                "result: RuleResult = evaluate_rule(rule=no_global_client, test_case=test_case)",
                "RuleFile` support sources are available to `ctx.project`",
                "## Cacheability",
                "Because `require_cacheable = true`",
                "allowlisted pure imports",
                "`open`, `eval`, `exec`, `input`, or `__import__`",
                "helpers inside configured rule packages",
                "fensu check --no-cache",
                "all hits, zero misses, `non_cacheable=0`",
                "## Blocking Rules",
                "### FFN001: validator-must-not-return",
                "### XAC001: approved-contract",
                "approved custom contract must hold",
                "Remediation: Restore the approved custom boundary.",
                "## Warning Rules",
                "### FFR706: descriptive-rule-module-names",
                "rule module filenames must describe their policy",
            ),
            expected_absent_fragments=(
                "_memoize",
                "analysis(path=path)",
                "name: fensu\n",
            ),
        ),
        SkillContentTestCase(
            description="selected custom rules explain per-rule cacheability declarations",
            context=custom_default_cache_generation_context(),
            expected_fragments=(
                "## Cacheability",
                "Configured cache enabled: `true`",
                "Configured `require_cacheable`: `false`",
                "Undeclared custom rules re-run fresh on every check",
                "Declare `cacheable=True` on `@rule`",
                "`require_cacheable = true`",
            ),
            expected_absent_fragments=("Because `require_cacheable = true`",),
        ),
        SkillContentTestCase(
            description="core-only context keeps mandatory sections without conditional claims",
            context=core_only_generation_context(),
            expected_fragments=(
                'Configuration source: "fensu.toml"',
                "- Warning selectors (`warn`): []",
                "- Warning rule codes: []",
                "## Working With Existing Drift",
                "## Testing Refactors Safely",
                "## Test Execution And Isolation",
                "## Custom Rule Authority",
                "## RuleContext Public API",
                "## Approved Custom Rule Authoring Lookup",
                "## Cacheability",
                "## Blocking Rules",
                "### FFH001: single-line-docstrings",
                "## Warning Rules\n\nNone.",
            ),
            expected_absent_fragments=(
                "## Warning Policy",
                "Selected custom rules disable persistent caching",
                "Because `require_cacheable = true`",
                "## Testing Custom Rules",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_complete_generation_context_when_rendering_then_includes_mandatory_policy(
    test_case: SkillContentTestCase,
) -> None:
    document: str = generate_skill(context=test_case.context)
    blocking_section: str = document.partition("## Blocking Rules")[2].partition(
        "## Warning Rules"
    )[0]

    assert all(fragment in document for fragment in test_case.expected_fragments)
    assert all(fragment not in document for fragment in test_case.expected_absent_fragments)
    assert "### FFR706:" not in blocking_section


@pytest.mark.parametrize(
    "test_case",
    [
        SkillDeterminismTestCase(
            description="reordered mappings catalogue and tiers produce identical UTF-8 bytes",
            first_context=comprehensive_generation_context(),
            second_context=comprehensive_generation_context(reverse_mappings=True),
            expected_equal=True,
        ),
        SkillDeterminismTestCase(
            description="implicit and explicit disabled memory preserve identical generated bytes",
            first_context=generation_context(
                config=Config(roots=("src/acme",), tests=(), tooling=()),
                blocking_rules=core_rules_for_codes(("FFH001",)),
            ),
            second_context=generation_context(
                config=Config(
                    roots=("src/acme",),
                    tests=(),
                    tooling=(),
                    experimental=ExperimentalConfig(memory=False),
                ),
                blocking_rules=core_rules_for_codes(("FFH001",)),
            ),
            expected_equal=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_equivalent_reordered_contexts_when_rendering_then_bytes_are_deterministic(
    test_case: SkillDeterminismTestCase,
) -> None:
    first: bytes = generate_skill(context=test_case.first_context).encode("utf-8")
    second: bytes = generate_skill(context=test_case.second_context).encode("utf-8")

    assert (first == second) is test_case.expected_equal
    assert b"\r" not in first
    assert first.endswith(b"\n")


@pytest.mark.parametrize(
    "test_case",
    [
        SkillDeterminismTestCase(
            description="memory activation changes generated skill input identity",
            first_context=generation_context(
                config=Config(
                    roots=("src/acme",),
                    tests=(),
                    tooling=(),
                    experimental=ExperimentalConfig(memory=False),
                ),
                blocking_rules=core_rules_for_codes(("FFH001",)),
            ),
            second_context=generation_context(
                config=Config(
                    roots=("src/acme",),
                    tests=(),
                    tooling=(),
                    experimental=ExperimentalConfig(memory=True),
                ),
                blocking_rules=core_rules_for_codes(("FFH001",)),
            ),
            expected_equal=False,
        ),
        SkillDeterminismTestCase(
            description="memory retention changes generated skill input identity",
            first_context=generation_context(
                config=Config(
                    roots=("src/acme",),
                    tests=(),
                    tooling=(),
                    experimental=ExperimentalConfig(memory=True),
                    memory=MemoryConfig(tasks=MemoryTasksConfig(archive_after_days=7)),
                ),
                blocking_rules=core_rules_for_codes(("FFH001",)),
            ),
            second_context=generation_context(
                config=Config(
                    roots=("src/acme",),
                    tests=(),
                    tooling=(),
                    experimental=ExperimentalConfig(memory=True),
                    memory=MemoryConfig(tasks=MemoryTasksConfig(archive_after_days=14)),
                ),
                blocking_rules=core_rules_for_codes(("FFH001",)),
            ),
            expected_equal=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_memory_config_when_fingerprinting_then_identity_tracks_generated_guidance(
    test_case: SkillDeterminismTestCase,
) -> None:
    first: str = skill_input_fingerprint(test_case.first_context)
    second: str = skill_input_fingerprint(test_case.second_context)

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        SkillContextImmutabilityTestCase(
            description="generation context rejects field mutation",
            context=core_only_generation_context(),
            expected_error_type=FrozenInstanceError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_generation_context_when_mutating_field_then_context_remains_immutable(
    test_case: SkillContextImmutabilityTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type):
        mutate_generation_context(
            context=test_case.context,
            field_name="identity",
            value="changed",
        )
