"""Generate agent guidance from the active rule catalogue."""

from __future__ import annotations

from strata.agentdocs.constants import GENERATED_MARKER
from strata.agentdocs.helpers.guidance import repository_guidance_lines
from strata.agentdocs.helpers.workflow import navigation_workflow_lines
from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec


def generate_skill(*, config: Config, rules: tuple[RuleSpec, ...]) -> str:
    """Render active rules as one SKILL.md-style document."""

    lines: list[str] = [
        "---",
        "name: strata",
        (
            "description: Use whenever Strata is mentioned or used, including installation, "
            "strata.toml configuration, strata check/rule/map/skills commands, SF diagnostics, "
            "repository architecture, or multi-module Python call-flow work."
        ),
        "---",
        "",
        GENERATED_MARKER,
        "",
        "# Strata",
        "",
        (
            "Strata checks code ownership, dependency boundaries, module roles, function shape, "
            "and test conventions. This skill is generated from the repository's active rules."
        ),
        "Load this guidance before running any `strata` command or changing Strata configuration.",
        "",
        "## Commands",
        "",
        "- Run `strata check` after architecture-relevant changes.",
        "- Run `strata rule <CODE>` to inspect a diagnostic and its remediation.",
        "- Run `strata map <SYMBOL>` for a conservative downstream project call tree.",
        "- Run `strata skills update` after changing rule selection or custom rules.",
        "",
    ]
    lines.extend(navigation_workflow_lines())
    active_codes: frozenset[str] = frozenset(rule.code for rule in rules)
    lines.extend(repository_guidance_lines(config=config, active_codes=active_codes))
    if config.rule_exceptions:
        lines.extend(
            (
                "## Active Rule Exceptions",
                "",
                (
                    "These centralized exceptions are exact and review-visible in `strata.toml`. "
                    "Do not broaden them or add inline suppression comments."
                ),
                "",
            )
        )
        for exception in config.rule_exceptions:
            lines.extend(
                (
                    f"- `{exception.rule}` in `{exception.path}`: "
                    f"{', '.join(f'`{symbol}`' for symbol in exception.symbols)}",
                    f"  Reason: {exception.reason}",
                )
            )
        lines.append("")
    lines.extend(
        (
            "## Active Rules",
            "",
            (
                "These are the enabled core and custom rules for the repository where this skill "
                "was generated. Do not assume disabled or ignored rules apply."
            ),
            "",
        )
    )
    for rule in rules:
        lines.extend(
            (
                f"## {rule.code}: {rule.slug}",
                "",
                f"Family: `{rule.family.value}`",
                "",
                rule.message,
                "",
                f"Remediation: {rule.remediation or 'No remediation provided.'}",
                "",
            )
        )
    return "\n".join(lines).rstrip() + "\n"
