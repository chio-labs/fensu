<p align="center">
  <img src="https://raw.githubusercontent.com/chio-labs/strata/main/.github/strata-logo-wide.png" alt="Strata" width="100%">
</p>

<p align="center">
  Keep Python architecture executable.
</p>

**Most linters catch bad code inside files. Strata catches architectural drift:
code crossing the wrong boundary, living in the wrong module, or growing into the
wrong shape.**

As a repository grows, code moves, lessons get forgotten, and the mental map
decays. Tests preserve behavior and types preserve interfaces. Strata makes the
repository's architectural expectations executable.

Strata enforces:

- which layers may import which;
- what each module or role file may contain;
- whether orchestrator functions stay small;
- whether dataflow and mutation are explicit;
- whether names such as `validate_*` mean what they claim.

It ships a coherent default architecture rather than a blank rule framework, then
lets projects disable, extend, or replace parts deliberately.

Strata is functional and self-hosting, but remains pre-release.

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
```

Then run:

```bash
strata check
```

All rule families are enabled by default. Product roots and tooling receive
structural rules; tests receive test-convention and annotation rules.

## Default Structure

Product code uses domain, subdomain, then role. Tests mirror the code they cover;
tooling uses one ownership level because `scripts/` already establishes the outer
boundary.

```text
src/my_package/
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

## Core Commands

```bash
strata check
strata rule SFS131
strata map run_plan --depth 3
```

`strata check` enforces the configured architecture, `strata rule` explains one
rule and its remediation, and `strata map` renders a conservative downstream call
tree. Mapping does not require Strata configuration or rule adoption.

## Philosophy

Strata is strict by default wherever it can make an honest deterministic claim.
Following the rules should remove repeated architectural decisions from everyday
work. Deliberate differences belong in selection, configuration, or custom rules,
where they remain visible, rather than in scattered inline suppressions.

## Agent Skills

Generate repository-aware guidance from the active ruleset:

```bash
strata skills update
strata skills update --global
```

The generated skill includes Strata usage, rule-supported architecture examples,
navigation and work-handoff guidance, and every enabled core and custom rule.
Existing user-authored skill files are preserved unless `--force` is supplied.

## Custom Rules

Custom checks use `X...` codes and the same `RuleContext` as core rules. Once
configured, they participate in `strata check`, `strata rule`, and generated agent
skills. See the
[custom-rule guide](https://github.com/chio-labs/strata-docs/blob/main/concepts/custom-rules.mdx)
for the complete API and configuration.

## Documentation

The quickstart, architecture model, configuration reference, adoption guide, and
CLI reference live in the
[Strata documentation repository](https://github.com/chio-labs/strata-docs).

## Development

```bash
make verify
```

This runs formatting, static typing, Strata's self-check, and the full test suite.
