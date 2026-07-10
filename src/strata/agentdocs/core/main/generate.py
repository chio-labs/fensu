"""Generate agent guidance from the active rule catalogue."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec


def generate_skill(*, rules: tuple[RuleSpec, ...]) -> str:
    """Render active rules as one SKILL.md-style document."""

    lines: list[str] = [
        "# Strata Architecture Rules",
        "",
        "This project is checked by Strata. Follow these active rules when changing code.",
        "",
    ]
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
