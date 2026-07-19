"""Generate agent guidance from the active rule catalogue."""

from __future__ import annotations

import json
from pathlib import Path

from fensu.agentdocs._helpers.authoring import (
    authoring_lookup_lines,
    cacheability_lines,
    rule_context_lines,
    rule_testing_lines,
)
from fensu.agentdocs._helpers.effective_config import (
    effective_config_lines,
    warning_policy_lines,
)
from fensu.agentdocs._helpers.guidance import (
    configured_threshold_override_lines,
    memory_retrieval_guidance_lines,
    repository_guidance_lines,
)
from fensu.agentdocs._helpers.work_practices import (
    custom_rule_authority_lines,
    work_practice_lines,
)
from fensu.agentdocs._helpers.workflow import navigation_workflow_lines
from fensu.agentdocs.constants import GENERATED_MARKER
from fensu.agentdocs.models import SkillGenerationContext
from fensu.config.models import Config
from fensu.rules.authoring.models import RuleSpec


def generate_skill(*, context: SkillGenerationContext) -> str:
    """Render active rules as one SKILL.md-style document."""

    config: Config = context.config
    active_rules: tuple[RuleSpec, ...] = (*context.blocking_rules, *context.warning_rules)
    lines: list[str] = [
        "---",
        f"name: {json.dumps(context.identity, ensure_ascii=True)}",
        "description: "
        + json.dumps(
            f"Use when modifying the {context.identity.removeprefix('fensu-')} project governed "
            f"by {_governed_path(context)}. Includes Fensu configuration, commands, FF "
            "diagnostics, repository architecture, and multi-module Python call-flow work.",
            ensure_ascii=True,
        ),
        "---",
        "",
        GENERATED_MARKER,
        "",
        "# Fensu",
        "",
        (
            "Fensu checks code ownership, dependency boundaries, module roles, function shape, "
            "and test conventions. This skill is generated from the repository's active rules."
        ),
        "Load this guidance before running any `fensu` command or changing Fensu configuration.",
        "",
        "## Commands",
        "",
        "- Run `fensu check` after architecture-relevant changes.",
        "- Run `fensu rule <CODE>` to inspect a diagnostic and its remediation.",
        "- Run `fensu map <SYMBOL>` for a conservative downstream project call tree.",
        "- Run `fensu skills` after changing rule selection or custom rules.",
        "",
    ]
    lines.extend(memory_retrieval_guidance_lines(config))
    lines.extend(navigation_workflow_lines())
    lines.extend(work_practice_lines())
    active_codes: frozenset[str] = frozenset(rule.code for rule in active_rules)
    lines.extend(
        repository_guidance_lines(
            config=config,
            active_codes=active_codes,
            project_prefix=context.project_prefix,
        )
    )
    lines.extend(configured_threshold_override_lines(config=config, active_codes=active_codes))
    lines.extend(effective_config_lines(context))
    lines.extend(warning_policy_lines(context))
    lines.extend(custom_rule_authority_lines())
    lines.extend(rule_context_lines())
    lines.extend(authoring_lookup_lines())
    lines.extend(rule_testing_lines(context))
    lines.extend(cacheability_lines(context))
    lines.extend(_tier_lines(heading="Blocking Rules", rules=context.blocking_rules))
    lines.extend(_tier_lines(heading="Warning Rules", rules=context.warning_rules))
    return "\n".join(lines).rstrip() + "\n"


def _tier_lines(*, heading: str, rules: tuple[RuleSpec, ...]) -> tuple[str, ...]:
    lines: list[str] = [f"## {heading}", ""]
    if not rules:
        return (*lines, "None.", "")
    for rule in sorted(rules, key=lambda item: item.code):
        lines.extend(
            (
                f"### {rule.code}: {rule.slug}",
                "",
                f"Family: `{rule.family.value}`",
                "",
                rule.message,
                "",
                f"Remediation: {rule.remediation or 'No remediation provided.'}",
                "",
            )
        )
    return tuple(lines)


def _governed_path(context: SkillGenerationContext) -> str:
    try:
        path: Path = context.config_source.path.resolve().relative_to(
            context.install_root.resolve()
        )
    except ValueError:
        path = context.config_source.path.resolve().relative_to(context.project_root.resolve())
    return path.as_posix()
