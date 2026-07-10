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
strata map package.module.run_plan --root src
strata map service.run --root services --root libraries
```

`strata map` does not require Strata configuration or architecture-rule adoption.
Explicit `--root` values are Python import roots and may be repeated. Without
explicit roots, map uses configured Strata roots when available, otherwise it
infers `src/` or falls back to the repository root.

Repository-relative paths are the default so terminals such as VS Code can make
locations clickable. Use `--paths absolute|relative|compact|none` to change the
display. ANSI color is automatic for terminals, can be controlled with
`--color auto|always|never`, and respects `NO_COLOR`.

The current provider resolves top-level project functions through same-module
calls, absolute and relative direct imports, module aliases, namespace packages,
and multiple import roots. Calls remain in source order. Dynamic dispatch is not
guessed; calls through function parameters are displayed as unresolved seams.
Ambiguous bare names require a dotted or `path::function` selector. Cycles and
depth truncation are marked in both colored and plain output.

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
