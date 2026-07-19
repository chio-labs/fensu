"""Helpers for repository-aware skill guidance tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from fensu.agentdocs.models import SkillGenerationContext
from fensu.config.constants import DEFAULT_THRESHOLDS
from fensu.config.models import (
    CacheConfig,
    Config,
    ConfigSource,
    EvaluationConfig,
    RuleExceptionEntry,
    ThresholdOverride,
)
from fensu.config.types import ConfigSourceKind
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family, RuleKind, Threshold
from fensu.rules.catalog.constants import CORE_RULES


def core_rules_for_codes(rule_codes: tuple[str, ...]) -> tuple[RuleSpec, ...]:
    """Return core rules in the requested order."""

    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in CORE_RULES}
    return tuple(rules_by_code[code] for code in rule_codes)


def core_rule_codes_for_prefix(prefix: str) -> tuple[str, ...]:
    """Return core rule codes that share a family prefix."""

    matching_rules: filter[RuleSpec] = filter(lambda rule: rule.code.startswith(prefix), CORE_RULES)
    return tuple(rule.code for rule in matching_rules)


def generation_context(
    *,
    config: Config,
    blocking_rules: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    ignored_rules: tuple[RuleSpec, ...] = (),
    catalogue: tuple[RuleSpec, ...] = (),
    source_kind: ConfigSourceKind = ConfigSourceKind.FENSU_TOML,
) -> SkillGenerationContext:
    """Build one deterministic unit-test generation context."""

    project_root: Path = Path("/project")
    source_name: str = {
        ConfigSourceKind.PYPROJECT: "pyproject.toml",
        ConfigSourceKind.FENSU_TOML: "fensu.toml",
    }[source_kind]
    return SkillGenerationContext(
        config_source=ConfigSource(path=project_root / source_name, kind=source_kind),
        project_root=project_root,
        install_root=project_root,
        git_root=None,
        project_prefix="",
        identity="fensu-project",
        catalogue=catalogue or blocking_rules,
        blocking_rules=blocking_rules,
        warning_rules=warning_rules,
        ignored_rules=ignored_rules,
        config=config,
    )


def comprehensive_generation_context(*, reverse_mappings: bool = False) -> SkillGenerationContext:
    """Build a context exercising every effective-policy snapshot class."""

    threshold_items: list[tuple[Threshold, int]] = list(DEFAULT_THRESHOLDS.items())
    role_items: list[tuple[str, MappingProxyType[Threshold, int]]] = [
        (
            "main",
            MappingProxyType(
                {
                    Threshold.MAX_ROLE_DEPTH: 2,
                    Threshold.MAX_MAIN_CONTAINER_MODULES: 24,
                }
            ),
        ),
        ("helpers", MappingProxyType({Threshold.MAX_HELPERS_CONTAINER_MODULES: 14})),
    ]
    contract_items: list[tuple[str, str]] = [
        ("fetch_*", "returns-value"),
        ("is_*", "returns-bool"),
    ]
    threshold_items = list(
        {False: tuple(threshold_items), True: tuple(reversed(threshold_items))}[reverse_mappings]
    )
    role_items = list(
        {False: tuple(role_items), True: tuple(reversed(role_items))}[reverse_mappings]
    )
    contract_items = list(
        {False: tuple(contract_items), True: tuple(reversed(contract_items))}[reverse_mappings]
    )
    config: Config = Config(
        roots=('src/"quoted"', "lib/pkg"),
        tests=("checks", "tests"),
        tooling=("tools", "scripts"),
        select=("XAC001", "FFN"),
        warn=("FFR706",),
        ignore=("FFH001",),
        rule_paths=("scripts/fensu/rules/client_ownership.py", "scripts/other_rules"),
        rule_modules=("acme.policy", "acme.more_policy"),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XAC001",
                path='src/"quoted"/client.py',
                symbols=("Client.run",),
                reason="External `API` contract.\nReviewed.",
            ),
            RuleExceptionEntry(
                rule="FFN001",
                path="lib/pkg/legacy.py",
                reason="Generated callback.",
            ),
        ),
        cache=CacheConfig(enabled=True, require_cacheable=True),
        evaluation=EvaluationConfig(
            include=("src/**/*.py", "lib/**/*.py"),
            exclude=("src/generated/**",),
        ),
        thresholds=MappingProxyType(dict(threshold_items)),
        role_thresholds=MappingProxyType(dict(role_items)),
        threshold_overrides=(
            ThresholdOverride(
                paths=("src/**/main/*.py", "lib/**/main/*.py"),
                thresholds=MappingProxyType(
                    {
                        Threshold.MAX_STATEMENTS: 35,
                        Threshold.MAX_DISTINCT_CALLS: 18,
                    }
                ),
                reason="Focused orchestration.",
            ),
        ),
        contracts=MappingProxyType(dict(contract_items)),
    )
    naming_rule: RuleSpec = core_rules_for_codes(("FFN001",))[0]
    warning_rule: RuleSpec = core_rules_for_codes(("FFR706",))[0]
    ignored_rule: RuleSpec = core_rules_for_codes(("FFH001",))[0]
    custom_rule: RuleSpec = replace(
        naming_rule,
        code="XAC001",
        family=Family.CUSTOM,
        slug="approved-contract",
        message="approved custom contract must hold",
        remediation="Restore the approved custom boundary.",
        kind=RuleKind.CUSTOM,
        source="scripts/fensu/rules/client_ownership.py",
        cacheable=True,
    )
    original_catalogue: tuple[RuleSpec, ...] = (
        ignored_rule,
        custom_rule,
        warning_rule,
        naming_rule,
    )
    original_blocking: tuple[RuleSpec, ...] = (custom_rule, naming_rule)
    catalogue: tuple[RuleSpec, ...] = {
        False: original_catalogue,
        True: tuple(reversed(original_catalogue)),
    }[reverse_mappings]
    blocking: tuple[RuleSpec, ...] = {
        False: original_blocking,
        True: tuple(reversed(original_blocking)),
    }[reverse_mappings]
    return generation_context(
        config=config,
        blocking_rules=blocking,
        warning_rules=(warning_rule,),
        ignored_rules=(ignored_rule,),
        catalogue=catalogue,
        source_kind=ConfigSourceKind.PYPROJECT,
    )


def custom_default_cache_generation_context() -> SkillGenerationContext:
    """Build a selected-custom-rule context without required cacheability."""

    context: SkillGenerationContext = comprehensive_generation_context()
    config: Config = replace(
        context.config,
        cache=CacheConfig(enabled=True, require_cacheable=False),
    )
    return replace(context, config=config)


def core_only_generation_context() -> SkillGenerationContext:
    """Build a context with no warning or custom rules configured."""

    rule: RuleSpec = core_rules_for_codes(("FFH001",))[0]
    return generation_context(
        config=Config(roots=("src/acme",), tests=(), tooling=()),
        blocking_rules=(rule,),
    )


def mutate_generation_context(
    *, context: SkillGenerationContext, field_name: str, value: object
) -> None:
    """Attempt one ordinary field assignment for immutability coverage."""

    setattr(context, field_name, value)


def structure_fragment_is_absent(*, document: str, fragment: str) -> bool:
    """Return whether a structural claim is absent from its generated scope."""

    guidance: str = document.partition("## Effective Project Configuration")[0]
    structure: str = guidance.partition("## Repository Structure")[2]
    inspected_scope: str = {False: structure, True: guidance}[fragment.startswith("## ")]
    return fragment not in inspected_scope
