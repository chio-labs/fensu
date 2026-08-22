# fensu-structure-checker

`fensu-structure-checker` enforces explicit Rust workspace structure and code
shape conventions. Its default configuration checks Fensu, while `--config`
accepts versioned consumer identities and parser-boundary policy for other
repositories.

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
```

Run the checker from a Cargo workspace root:

```console
fensu-structure-checker --config rust-structure-checker.toml
```
