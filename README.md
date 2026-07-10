# Strata

Strata is an opinionated architecture linter for Python repositories. It checks
where code lives, which boundaries imports may cross, what role each module
plays, and whether functions make control flow, state, and data ownership clear.

> Most linters catch bad code. Strata catches code that is in the wrong place,
> the wrong shape, or dishonest about what it does.

The project is functional and self-hosting, but remains pre-release.

## Installation

```bash
pip install stratalint
```

The distribution name is `stratalint`; the installed command is `strata`.

## Quick Start

Add `strata.toml` at the repository root:

```toml
roots = ["src/my_package"]
tests = ["tests"]
tooling = ["scripts"]
select = ["SF"]

[thresholds]
max_positional_args = 1
```

Then run:

```bash
strata check
strata skills update
```

Product roots and tooling receive structural rules. Tests receive test and
annotation rules.

## Default Structure

Strata's default architecture uses two ownership levels before role-oriented
modules and packages. Tests mirror the code they cover; tooling uses one ownership
level because `scripts/` already establishes the outer boundary.

```text
src/my_package/
├── __init__.py
└── domain/
    └── subdomain/
        ├── main/
        │   └── run.py
        ├── helpers/
        ├── classes/
        ├── models.py
        ├── types.py
        ├── constants.py
        └── exceptions.py
tests/unit/src/my_package/domain/subdomain/
├── _test_types.py
└── test_run.py
scripts/
├── run_tool.py
└── tool_name/
    ├── main/
    ├── helpers/
    └── classes/
```

Direct `scripts/*.py` files are thin command adapters. Supporting logic belongs
under `scripts/<tool>/<role>/`.

## Commands

Check the configured repository and inspect rule metadata:

```bash
strata check
strata rule SFS131
```

Install repository-aware agent skills. Repository-local installation is the
default; `--global` writes to the corresponding user-level agent directories.

```bash
strata skills update
strata skills update --global
strata skills update --target opencode --target agents
```

The generated skill includes concise Strata usage, the default structure, and
every enabled core and custom rule from the current repository. Existing
user-authored skill files are preserved unless `--force` is supplied.

Render a conservative downstream call tree:

```bash
strata map run_plan --depth 3
strata map path/to/module::run_plan
strata map package.module.run_plan --root src
```

`strata map` does not require Strata configuration or architecture-rule adoption.
It resolves statically knowable project-function calls without guessing dynamic
dispatch. Use `strata map --help` for root, path, depth, and color controls.

## Custom Rules

Custom checks use `X...` codes and the same `RuleContext` as core rules:

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

Keep project-local rules in the tooling tree:

```text
scripts/strata_rules/rules/
├── boundaries.py
└── naming.py
```

Configure and enable them in `strata.toml`:

```toml
tooling = ["scripts"]
rule_paths = ["scripts/strata_rules/rules"]
rule_modules = ["company_architecture.rules"]
select = ["SF", "XAC001"]
```

Custom rules are included by `strata check`, `strata rule`, and
`strata skills update` once configured.

`SFX007` requires string comparison values to be named, and `SFX008` does the
same for numeric comparison values other than `-1`, `0`, and `1`.

## Philosophy

Strata ships a coherent default architecture instead of a blank rule framework.
Rules are strict by default where the tool can make an honest deterministic
claim. A rule that overclaims should be fixed; a deliberate project difference
should be expressed through selection, configuration, or a custom rule rather
than scattered inline suppressions.

The project dogfoods this contract: `make verify` runs formatting, static typing,
`strata check`, and the full test suite.
