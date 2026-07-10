"""Generate agent guidance from the active rule catalogue."""

from __future__ import annotations

from strata.agentdocs.core.constants import GENERATED_MARKER
from strata.rules.authoring.models import RuleSpec


def generate_skill(*, rules: tuple[RuleSpec, ...]) -> str:
    """Render active rules as one SKILL.md-style document."""

    lines: list[str] = [
        "---",
        "name: strata",
        "description: Use Strata to inspect and enforce this Python repository's architecture.",
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
        "",
        "## Commands",
        "",
        "- Run `strata check` after architecture-relevant changes.",
        "- Run `strata rule <CODE>` to inspect a diagnostic and its remediation.",
        "- Run `strata map <SYMBOL>` for a conservative downstream project call tree.",
        "- Run `strata skills update` after changing rule selection or custom rules.",
        "",
        "## Default Repository Shape",
        "",
        "```text",
        "src/my_package/",
        "└── domain/",
        "    └── subdomain/",
        "        ├── main/",
        "        ├── helpers/",
        "        ├── classes/",
        "        ├── models.py",
        "        ├── types.py",
        "        ├── constants.py",
        "        └── exceptions.py",
        "tests/unit/src/my_package/domain/subdomain/",
        "scripts/",
        "├── run_tool.py",
        "└── tool_name/",
        "    ├── main/",
        "    └── helpers/",
        "```",
        "",
        (
            "Keep runtime ownership explicit, mirror runtime and tooling paths under tests, and "
            "keep direct scripts as thin adapters into role-oriented tool packages."
        ),
        "",
        "## Active Rules",
        "",
        (
            "These are the enabled core and custom rules for the repository where this skill was "
            "generated. Do not assume disabled or ignored rules apply."
        ),
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
