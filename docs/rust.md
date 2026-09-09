# Rust analyzer

Fensu owns Rust parsing, Cargo discovery, workspace facts, and all Rust rules in `fensu-rust`.
Use the normal `fensu` command and `fensu.toml` configuration.

```toml
[targets.rust]
analyzer = "rust"
roots = ["crates"]
tests = []
tooling = []
rule_packs = ["rust"]
select = ["FPRS"]
```

```sh
fensu check --target rust
```

For a single package, set `roots = ["src"]`. For a Cargo project below the repository root,
set the target's `root` to that project directory. Paths in target settings are relative to
that target root. Cargo discovers workspace membership, package identities, library and binary
targets, and integration-test targets. No crate inventory is required.

The pack enables all 117 implemented Rust rules by default. The original structural budgets
and rule behavior are retained. Use `select`, `warn`, `ignore`, `rule_exceptions`, and
`rule_ignores` as for other analyzers. Rust exceptions identify files, including `Cargo.toml`;
they do not use Python definition selectors.

## Rule options

All adjustments belong under the owning rule in the target's `rule_options` table:

```toml
[targets.rust.rule_options.FPRSS010]
max_arguments = 8

[targets.rust.rule_options.FPRSR601]
max_file_lines = 1500
```

| Rule | Option | Default |
| --- | --- | --- |
| `FPRSR601` | `max_file_lines` | 2000 |
| `FPRSS010` | `max_arguments` | 10 |
| `FPRSS011` | `max_statements` | 70 |
| `FPRSS001` | `max_statements` | 40 |
| `FPRSS002` | `max_distinct_calls` | 20 |
| `FPRSS003` | `max_locals` | 20 |
| `FPRSR301` | `max_modules` | 10 |
| `FPRSR302` | `max_modules` | 20 |

Budgets must be positive integers. Unknown option names are rejected.

## Repository boundaries

Repository-specific identities are opt-in. Default analysis has no Fensu package allowlist
and no restriction on a particular third-party parser.

Use normal `tooling` paths to identify tooling crates. Tooling crates receive the tooling
layout rules, including `FPRSR704`, `FPRSR705`, and `FPRSR706`. Dependency restrictions apply
to runtime crates outside those tooling paths:

```toml
[targets.rust]
analyzer = "rust"
roots = ["crates"]
tooling = ["crates/project-tools"]
rule_packs = ["rust"]
select = ["FPRS"]

[targets.rust.rule_options.FPRSL301]
forbidden_packages = ["project-tools"]

[targets.rust.rule_options.FPRSL102]
packages = ["syntax-parser"]
restricted_paths = ["rules"]
remediation = "consume shared fact models instead of parser types"
```

`FPRSL301.forbidden_packages` defaults to an empty list. `FPRSL102.packages` also defaults to
an empty list; `restricted_paths` defaults to `["rules"]`. A single path component matches
that directory name in library sources. A path containing `/` identifies an exact target-relative
subtree, including test sources. Dependency aliases are resolved when matching parser packages.

Optional closed inventories are available through `FPRSL304.crate_names` and
`FPRSL305.domain_paths` / `role_paths`; empty lists use automatic discovery without a closed
inventory. `FPRSL305.intentional_layout_paths` excludes explicit subtrees from aggregate layout
checks while preserving per-file checks. Paths must be canonical target-relative POSIX paths;
overlapping intentional paths and overlaps with declared structural paths are rejected.

## Cache and Cargo metadata

Rust sources, Cargo manifests, existing lockfiles, and target settings are cache inputs.
Existing lockfiles are read with locked metadata resolution. Lock-free workspaces use declared
dependency metadata without creating a lockfile. A Cargo metadata setup failure produces a
diagnostic and prevents caching, even if that diagnostic is excluded by rule selection.
