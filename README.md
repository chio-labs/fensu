# Strata

Strata is an opinionated architecture linter for Python repositories. It checks
where code lives, which boundaries imports may cross, what role each module
plays, and whether functions make control flow, state, and data ownership clear.

> Most linters catch bad code. Strata catches code that is in the wrong place,
> the wrong shape, or dishonest about what it does.

The distribution name is `stratalint`; the command is `strata`. The project is
functional and self-hosting, but remains pre-release.

## Current Usage

From a development checkout:

```bash
uv sync
uv run strata check
```

Strata reads `strata.toml` from the repository:

```toml
roots = ["src/my_package"]
tests = ["tests"]
tooling = ["scripts"]
select = ["SF"]

[thresholds]
max_positional_args = 1
```

The configured scopes receive different policies: product roots get structural
rules, tests get test and annotation rules, and tooling gets a deliberately
smaller boundary/hygiene set.

## Commands

Check the configured repository:

```bash
strata check
```

Inspect the single-sourced metadata for a core or configured custom rule:

```bash
strata rule SFS131
```

Generate a SKILL.md-style document from the project's active rules:

```bash
strata skill
strata skill --output .agents/skills/strata/SKILL.md
```

Render a conservative downstream call tree:

```bash
strata map run_plan --depth 3
strata map path/to/module::run_plan
```

The current map provider resolves top-level project functions through same-module
calls, direct imports, and module aliases. Dynamic dispatch and unresolved calls
are not guessed; calls through function parameters are displayed as unresolved
seams. Ambiguous bare names require a dotted or `path::function` selector; cycles
and depth truncation are marked in the output.

## Custom Rules

Custom checks use `X...` codes and the same `RuleContext` available to core rules:

```python
from __future__ import annotations

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XAC001",
    family=Family.CUSTOM,
    slug="no-acme-global",
    message="ACME_GLOBAL hides ownership",
    remediation="Move the value to the module that owns and produces it.",
)
def no_acme_global(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return [
        ctx.fault(node)
        for node in ctx.nodes(ast.Name)
        if isinstance(node, ast.Name) and node.id == "ACME_GLOBAL"
    ]
```

Load custom files or importable modules from configuration:

```toml
rule_paths = ["strata_rules"]
rule_modules = ["company_architecture.rules"]
select = ["SF", "XAC001"]
```

Custom rules are included by `strata rule` and `strata skill` once configured.

## Philosophy

Strata ships a coherent default architecture instead of a blank rule framework.
Rules are strict by default where the tool can make an honest deterministic
claim. A rule that overclaims should be fixed; a deliberate project difference
should be expressed through selection, configuration, or a custom rule rather
than scattered inline suppressions.

The project dogfoods this contract: `make verify` runs formatting, static typing,
`strata check`, and the full test suite.
