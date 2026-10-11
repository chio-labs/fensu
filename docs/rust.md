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

The pack enables all implemented Rust rules by default.
Use `select`, `warn`, `ignore`, `rule_exceptions`, and
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
| `FPRSS012` | `max_tuple_arity` | 3 |
| `FPRSS001` | `max_statements` | 40 |
| `FPRSS002` | `max_distinct_calls` | 20 |
| `FPRSS003` | `max_locals` | 20 |
| `FPRSR301` | `max_modules` | 10 |
| `FPRSR302` | `max_modules` | 20 |

Budgets must be positive integers. Unknown option names are rejected.

## Comments and tuple types

`FPRSH002` rejects every non-doc comment in library sources, including trailing `//`
comments and inline or standalone `/* */` blocks. Comment markers inside string, raw string,
byte, C string, and character literals are ignored. Nested block comments are one comment.
Rust doc comments (`///`, `//!`, `/** */`, `/*! */`) are allowed; `////`, `/**/`, and
`/*** */` are ordinary comments. `FPRSH001` limits adjacent doc-comment lines and each
block doc comment to one line.

`FPRSS012` (`rust-rss012`) limits tuple **types** to three elements by default. This applies
throughout source type positions, including aliases, fields, signatures, local and closure
annotations, generic arguments, nested tuples, associated constants, and statics. Replace
wide tuples with named structs whose fields explain each position. Tuple expressions,
patterns, and `()` are not flagged. Macro bodies remain opaque, like other `syn`-based
shape checks.

```toml
[targets.rust.rule_options.FPRSS012]
max_tuple_arity = 4
```

These checks make the Rust pack stricter: code that previously passed with trailing/block
comments or wide tuple types can now report faults after upgrading.

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
## File placement and embedded resources

The `rust` pack enables `FPRSR311` (`rust-rsr311`) and `FPRSL106` (`rust-rsl106`)
by default. Upgrading can therefore report new faults for package-root data directories
or includes that cross ownership boundaries.

`FPRSR311` checks each Cargo-discovered package directory, reporting one fault per
non-standard direct entry. Defaults allow `Cargo.toml`, `build.rs`, `src/`, `tests/`,
`benches/`, `examples/`, `README*`, and `LICENSE*`. `Cargo.lock` is always accepted.
Hidden entries, repository-local `.gitignore` matches, and `target/` are skipped.
Directories containing other workspace packages are also accepted when the workspace
root is itself a package.
Virtual workspace roots are not package directories and are not checked.

The `allowed_entries` option replaces the default list. Entries are filename glob
patterns; a trailing `/` requires a directory. For example:

```toml
[targets.rust.rule_options.FPRSR311]
allowed_entries = [
  "Cargo.toml", "build.rs", "src/", "tests/", "benches/", "examples/",
  "README*", "LICENSE*", "NOTICE*",
]
```

`FPRSL106` checks `include_str!` and `include_bytes!`, including `std::` and `core::`
forms, in parsed items, expressions, constants, statics, and nested macro token streams.
Nested invocations are inspected independently of the enclosing macro's grammar,
including repetition syntax such as `vec![include_str!("data.txt"); 2]`.
Each argument must be a single string literal: `concat!`, `env!`, identifiers, and
other computed arguments are faults. Paths resolve relative to the including file;
canonicalization resolves `..` and symlinks before checking the boundary. Missing,
unresolvable, and non-file targets are faults.

The boundary is the including file's top-level domain below its effective ownership
root, using the same longest configured `ownership_roots` match as the Rust ownership
rules (or the Cargo source root by default). Files directly at that root, including
`lib.rs` and `main.rs`, have no domain and cannot embed resources. Includes cannot
reach another domain, the source root, or outside the source tree. For example,
`src/orders/_helpers/read.rs` may include `../data/file.txt`, but not
`../../customers/data/file.txt`. Integration-test files use their discovered test
source root and must likewise keep embedded fixtures inside their own test domain.

Both rules support result caching, including default Rust-pack and mixed-target runs.
Before reading the cache, Cargo package/source discovery supplies deterministic observations:
package direct-entry names and file/directory/symlink kinds, applicable `.gitignore`
paths and contents (including missing files), and each literal include's canonical
target path or resolution failure and target file type. Source fingerprints cover
literal edits, non-literal arguments, and parse failures. Hidden entries and generated
`target/` directories are permanently skipped and do not invalidate placement results.

Package-entry ignore matching consults only `.gitignore` files from the nearest Git
repository root through the package directory, inclusive; without a `.git` marker,
the Cargo workspace root is the boundary. Nearer matching rules take precedence.
It does not consult parent directories above that root, `.ignore`, global Git ignore
configuration, or `.git/info/exclude`. The rule and cache observer share the same
ignore-input discovery. Unreadable observation inputs fail the check explicitly rather
than returning potentially stale cached output.
