# fensu-structure-checker

`fensu-structure-checker` enforces explicit Rust workspace structure and code
shape conventions. Its default configuration checks Fensu, while `--config`
accepts versioned consumer identities, structural paths and budgets, intentional
layout roots, and parser-boundary policy for other repositories.

The standalone command remains a compatibility surface. The primary Fensu integration is the
owned `fensu-rust` engine and `analyzer = "rust"`, which expose these checks through normal Fensu
rule selection, caching, exceptions, and reporting under `FPRS*` rule identities.

```toml
schema-version = 1

[tooling]
package = "example-structure-checker"
runtime-forbidden-packages = [
  "example-structure-checker",
  "fensu-structure-checker",
]
runtime-allowed-packages = []

[raw-parser-boundary]
packages = []
remediation = "consume shared fact rows instead of raw parser types"
restricted-paths = ["crates/example/src/rules"]

[repository]
crate-names = ["example"]
domain-paths = ["crates/example/src/analysis"]
role-paths = [
  "crates/example/src/analysis/main",
  "crates/example/src/analysis/models.rs",
]
intentional-layout-paths = ["crates/example/src/generated"]

[repository.thresholds]
max-file-lines = 2000
max-arguments = 10
max-statements-global = 70
max-statements-entry = 40
max-distinct-calls-entry = 20
max-locals-entry = 20
max-helper-container-modules = 10
max-main-container-modules = 20
```

The checker asks Cargo for its actual workspace packages, target source paths,
and dependency identities, so root packages, implicit path-dependency members,
inherited dependencies, and renamed dependencies cannot bypass policy. Library,
binary, and integration-test targets must use conventional `src/` and `tests/`
trees; unsupported custom paths fail closed instead of being recursively
guessed. Conventional examples, benchmarks, and build scripts are outside
aggregate architecture rules. An excluded target entry beneath `src/` or
`tests/` fails closed and remains scanned because it may also be a compiled
module. Workspace-wide reference checks resolve dependency aliases and custom
library names to the same Cargo identity. Local packages, targets, dependencies,
the config file, and every configured path must remain canonically contained by
the repository. Symlink entries inside Rust source trees are rejected rather
than silently skipped.

When a workspace has `Cargo.lock`, exact dependency resolution runs with `--locked`; a stale lock
is reported rather than rewritten. Lock-free library workspaces use Cargo's declared dependency
metadata, and checking never creates a lockfile.

`runtime-forbidden-packages` keeps checker/tooling implementations out of normal runtime crates.
`runtime-allowed-packages` is a narrow package-identity allowlist for an intentional engine facade;
all other runtime crates continue to receive the dependency violation.

`restricted-paths` selects the subtrees where raw-parser references are banned.
An exact repository-relative path selects that subtree. The single-component
default `rules` preserves the original behavior by selecting every directory
named `rules`. The parser check covers `use`, `extern crate`, type/expression
paths, macro paths, and parser identifiers inside macro token bodies. Omitting
`restricted-paths` retains that legacy default.

Intentional layout paths exclude only aggregate role-layout checks. Per-file
hygiene, dependency, raw-parser, shape, and test policies remain active. An
intentional root must be narrower than a Cargo source root and cannot overlap
another intentional root or a declared domain/role path. Configured paths are
canonical repository-relative POSIX text. Role paths may name a
`main`/`_helpers` container or an exact reserved role file. Once `domain-paths`
or `role-paths` is nonempty, that collection is a closed inventory: every
discovered path of that kind must be declared. Empty collections preserve the
default open-inventory behavior. Stale or empty declarations are rejected, and
declared roles must belong to a declared domain when the domain inventory is
closed.

Run the checker from a Cargo workspace root:

```console
fensu-structure-checker --config rust-structure-checker.toml
```
