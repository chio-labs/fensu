<p align="center">
  <img src="https://raw.githubusercontent.com/chio-labs/fensu/main/.github/fensu-logo-wide.png" alt="Fensu" width="100%">
</p>

<p align="center">
  Keeping Python repos from turning into spaghetti.
</p>

**Most linters catch bad code inside files. Fensu catches architectural drift:
code crossing the wrong boundary, living in the wrong module, or growing into the
wrong shape.**

As a repository grows, code moves, lessons get forgotten, and the mental map
decays. Tests preserve behavior and types preserve interfaces. Fensu makes the
repository's architectural expectations executable.

Fensu enforces:

- which layers may import which;
- what each module or role file may contain;
- whether orchestrator functions stay small;
- whether dataflow and mutation are explicit;
- whether names such as `validate_*` mean what they claim.

It ships a coherent default architecture rather than a blank rule framework, then
lets projects disable, extend, or replace parts deliberately.

Fensu is functional and self-hosting, but remains pre-release.

## Installation

```bash
pip install fensu
```

The authoring/API distribution is `fensu`. It installs the lockstep
`fensu-cli` binary package, which exclusively owns the `fensu` command.
Core-only `check`, `init`, `rule`, `map`, `skills`, `memory`, and `--version`
execution is native. Configured Python custom rules launch one compatible Python
host only for the policy metadata or callbacks they require.

Built-in commands are available only through the native `fensu` executable;
`python -m fensu` is retired. Installing `fensu-cli` from its source
distribution requires Rust.

Fensu requires Python 3.12+ and includes a compiled analysis core. Prebuilt
wheels cover Linux (x86_64, aarch64) and macOS (Intel, Apple silicon); on any
other platform, `pip` builds from source, which requires a Rust toolchain.
Release wheels are built for Windows x86_64 as well as the listed Linux and
macOS platforms.

## Quick Start

Detect the repository layout, choose a starting ruleset, and write a validated
configuration:

```bash
fensu init
```

For non-interactive setup, use `fensu init --yes`. To configure manually instead,
add `fensu.toml` at the repository root:

```toml
roots = ["src/my_package"]
tests = ["tests"]
tooling = ["scripts"]

[cache]
enabled = true
```

Then run:

```bash
fensu check
```

All rule families are enabled by default. Product roots and tooling receive
structural rules; tests receive test-convention and annotation rules.

## Default Structure

Product code uses domain, optional subdomain, then role. Every leaf domain or
subdomain owns meaningful behavior through a direct `main/` containing at least one
entry module. Branch-domain parents do not need their own `main/`; their leaf
subdomains do. Tests mirror the code they cover; tooling uses one ownership level
because `scripts/` already establishes the outer boundary.

```text
src/my_package/
└── domain/
    └── subdomain/
        ├── main/
        │   └── run.py
        ├── _helpers/
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
    ├── _helpers/
    └── classes/
```

Do not create an empty or initializer-only `main/` to satisfy the layout. If a
package contains only passive models, types, constants, exceptions, or classes,
move those declarations into the closest domain or subdomain whose `main/` behavior
owns and uses them. Fixed role files are siblings of `_helpers/`, never descendants
such as `_helpers/entry/models.py`.

Direct `scripts/*.py` files are thin command adapters. Supporting logic belongs
under `scripts/<tool>/<role>/`.

## Core Commands

```bash
fensu init
fensu check
fensu rule FFS131
fensu map run_plan --depth 3
```

`fensu init` detects and validates an onboarding configuration, `fensu check`
enforces the configured architecture, `fensu rule` explains one rule and its
remediation, and `fensu map` renders a conservative downstream call tree. Mapping
follows project functions and class methods when imports,
annotations, constructors, or return types prove the receiver. Calls through
protocols and untyped parameters remain visible as unresolved dispatch seams
rather than guessed implementations. Mapping does not require Fensu
configuration or rule adoption.

`fensu check` stores disposable evaluation results in a repository-local
SQLite database under `.fensu/cache/`
and reuses them only after validating source, configuration, rule, implementation,
and project-query inputs. Caching is enabled by default; set `cache.enabled = false`
in configuration or pass `--no-cache` for an explicit uncached check. `--cache`
overrides a disabled project preference for one invocation.
Deleting `.fensu/cache/` is always safe; ignore that directory rather than the
complete `.fensu/` namespace, which is reserved for other Fensu-owned state.

## Enforce It, Then See It

Because Fensu enforces the structure, it can also render it. `fensu map`
produces a deterministic downstream call tree with clickable `path:line`
locations, class-qualified method names, and explicit protocol seams while
marking unresolved dynamic calls, depth limits, and cycles.

```text
$ fensu map run_map --depth 4

run_map(...)  src/fensu/cli/main/map.py:21
├── _parser(...)  src/fensu/cli/main/map.py:53
├── resolve_mapping_project(...)  src/fensu/mapping/main/resolve_project.py:11
│   └── resolve_mapping_project(...)  src/fensu/mapping/_helpers/project.py:15
│       ├── _find_project_root(...)  src/fensu/mapping/_helpers/project.py:73
│       ├── _explicit_source(...)  src/fensu/mapping/_helpers/project.py:65
│       ├── _optional_config_source(...)  src/fensu/mapping/_helpers/project.py:38
│       │   └── find_config_source(...)  src/fensu/config/main/find_config.py:12  (depth limit)
│       └── _configured_project(...)  src/fensu/mapping/_helpers/project.py:45
│           ├── load_config(...)  src/fensu/config/main/load_config.py:15  (depth limit)
│           └── _configured_source(...)  src/fensu/mapping/_helpers/project.py:57
└── build_call_map(...)  src/fensu/mapping/main/build.py:12
    ├── provider(...)  src/fensu/mapping/main/build.py:24  (unresolved parameter call)
    └── render_tree(...)  src/fensu/mapping/_helpers/render.py:19
        ├── _child_lines(...)  src/fensu/mapping/_helpers/render.py:41
        │   └── _child_lines(...)  src/fensu/mapping/_helpers/render.py:41  (cycle)
        └── _label(...)  src/fensu/mapping/_helpers/render.py:88
```

The map is useful precisely because it is not guessing. `fensu check` enforces
layers, roles, and public surfaces first, and `fensu map` then renders the
structure the code is required to expose.

## Philosophy

Fensu is strict by default wherever it can make an honest deterministic claim.
Following the rules should remove repeated architectural decisions from everyday
work. Deliberate differences belong in selection, configuration, or custom rules,
where they remain visible, rather than in scattered inline suppressions.

Unavoidable external calling conventions can use exact symbol-scoped exceptions:

```toml
[[rule_exceptions]]
rule = "FFS120"
path = "src/my_package/integrations/_helpers/callbacks.py"
symbols = ["ProgressCollector.update"]
reason = "The external API invokes this callback positionally."
```

Exceptions accept one exact rule code, repository-relative Python file, and one
or more qualified symbols. Globs, directories, line numbers, path-only entries,
and inline suppression comments are not supported. `fensu check` rejects stale
exceptions that no longer suppress a fault.

## Agent Skills

Generate repository-aware guidance from the active ruleset:

```bash
fensu skills
fensu skills --global
```

The generated skill includes Fensu usage, rule-supported architecture examples,
navigation and work-handoff guidance, and every enabled core and custom rule.
Existing user-authored skill files are preserved unless `--force` is supplied.

## Custom Rules

Custom checks use `X...` codes and the same `RuleContext` as core rules. Once
configured, they participate in `fensu check`, `fensu rule`, and generated agent
skills. Rules can use `ctx.facts`, `ctx.project`, `ctx.text`, `ctx.syntax`, and
`ctx.relations`; these are the same backend-neutral analysis zones used by Fensu's
built-in rules. Project and filesystem reads made through `ctx.project` are tracked
for cache invalidation. Raw `ast.Module` access remains available for checks that need
unrestricted Python syntax traversal. Semantic fact contracts and author-facing models
are public Python APIs, while their production extraction has one native Rust owner;
raw AST, syntax, and relation artifacts remain lazy CPython capabilities. Keep
project-owned checks in the canonical
`scripts/fensu_policy/rules/` tooling role and load them explicitly:

```toml
tooling = ["scripts"]
rule_paths = ["scripts/fensu_policy/rules"]
```

See the [custom-rule guide](https://docs.fensu.dev/concepts/custom-rules)
for the complete API and configuration.

## Documentation

The quickstart, architecture model, configuration reference, adoption guide, and
CLI reference live at [docs.fensu.dev](https://docs.fensu.dev).
