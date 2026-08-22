# fensu-structure-checker

`fensu-structure-checker` enforces explicit Rust workspace structure and code
shape conventions. Its default configuration checks Fensu, while `--config`
accepts versioned consumer identities, structural paths and budgets, intentional
layout roots, and parser-boundary policy for other repositories.

```toml
schema-version = 1

[tooling]
package = "example-structure-checker"
runtime-forbidden-packages = [
  "example-structure-checker",
  "fensu-structure-checker",
]

[raw-parser-boundary]
packages = []
remediation = "consume shared fact rows instead of raw parser types"

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

Intentional layout paths exclude only aggregate role-layout checks. Per-file
hygiene, dependency, raw-parser, shape, and test policies remain active.
Configured paths are canonical repository-relative POSIX text. Role paths may
name a `main`/`_helpers` container or an exact reserved role file.

Run the checker from a Cargo workspace root:

```console
fensu-structure-checker --config rust-structure-checker.toml
```
