# Python dead-code enforcement

`fensu check` can enforce production reachability for Python module-level functions,
classes, constants, and modules. It never deletes code. Methods, parameters, and
model/configuration fields are not separate unused-member diagnostics in this milestone.
Other analyzers retain their existing rules.

## Enable explicitly

```toml
[dead_code]
enabled = true

[[dead_code.roots]]
modules = ["orders.cli.handlers.**"]
symbols = ["run_*"]
reason = "The command dispatcher loads handlers from its runtime string table."
```

Missing `dead_code`, `enabled = false`, or roots without `enabled = true` preserve existing
behavior. Deleting the final root does not disable enforcement. `fensu init` enables the
feature when scaffolding a blank Python project, but not when adopting existing code.
In `pyproject.toml`, use `[tool.fensu.dead_code]` and `[[tool.fensu.dead_code.roots]]`.
For named targets, place the section within the Python target configuration.

`modules` and `symbols` are non-empty arrays of glob patterns over dotted module names
and declaration names respectively. Literal patterns select exact names; `symbols = ["*"]`
deliberately keeps all matching declarations. These are symbol patterns, not filesystem
paths. Every root requires a non-empty reason. Unknown keys, invalid patterns, and malformed
values fail configuration validation, including when enforcement is disabled.

Roots match existing declarations before traversal. A declaration does not have to be
reachable already to match a root. A root matching no selected production declaration is
stale, including when its last matching declaration is removed or excluded from analysis.

## What stays live

- Deliberate static `__all__` exports and public bindings in root-package initializers.
- Exact `[project.scripts]`, `[project.gui-scripts]`, and `[project.entry-points]` references.
- `__main__` module execution and module interpreter hooks such as `__getattr__`.
- Dependencies reached from those roots, including imports, aliases, defaults, annotations,
  top-level execution, and all methods of a live class. Keeping all live-class methods
  preserves dunders and contract overrides without asserting method-level liveness.
- Recognized registrations: `atexit.register` and callbacks attached to statically identified
  Click groups, Typer applications, Flask applications/blueprints, and FastAPI applications/routers.
  Application callbacks are retained through the application; arbitrary decorators are not roots.
- Literal absolute `importlib.import_module` references, including direct member access and
   local and module-level aliases. Computed imports, indirect string registries, reflection, generated exports,
  and external framework registrations need explicit reasoned roots.

Importing a module executes its top-level code; it does not keep all of its helper bodies.
Unused cycles and helper chains do not become roots. Constant identity is module-scoped.
Tests never supply production roots and configured test sources are not dead-code subjects.
Neither `main/` placement nor non-underscore spelling is an API declaration.

This is a conservative static graph, not runtime coverage: both branches of conditional
imports may retain declarations, and methods of a live class remain live even when no
individual method call is found. It does not diagnose fields, parameters, enum members,
or unused methods. Dynamic dispatch that the graph cannot resolve can report a live
declaration until a reasoned root is supplied; keeping a class or public facade can
retain genuinely unused members. No runtime imports or application code are executed.

Analysis uses configured target source discovery and honors evaluation/generated exclusions.
Gitignore patterns do not silently hide a selected source directory such as `build/` or a hidden
directory. Documentation text and arbitrary files outside the configured analysis surface are
not Python symbol references; documented external APIs should be exported or configured explicitly.

## Diagnostics and workflow

| Code | Meaning |
| --- | --- |
| `FFL106` | Unreachable module-level function, class, or constant |
| `FFL107` | Configured root matches no existing production declaration |
| `FFL108` | Unreachable Python module |

These are blocking `check` faults. Use the existing rule-exception machinery for intentional
suppressions. Investigate the actual entry mechanism before removing a reported declaration;
do not erase deliberate public APIs or add unexplained roots merely to make checks green.

Configuration, source dependencies, and project metadata contribute to cache invalidation.
Changing roots or script/plugin metadata must affect the next cached check just as it affects
an uncached check.

## Public rule-authoring facts

Python rules can read `ctx.project.dead_code` (`DeadCodeConfig` containing typed
`DeadCodeRoot` values with `modules`, `symbols`, and `reason`) and call
`ctx.project.python_reachability()` to obtain a `PythonReachabilityFacts` snapshot:

- `symbols`: `PythonSymbolFact` values with snapshot-local `PythonSymbolId`, module,
  qualified declaration name, `PythonSymbolKind`, and `SourceLocation`.
- `references`: resolved `PythonReferenceFact` source/target edges, including edges owned
  by module execution. Aliases, reexports, annotations, defaults, literal imports, and
  recognized registrations are resolved by the same analysis used by the native rules.
- `entrypoints`: `PythonEntryPointFact` values with `PythonEntryPointKind`, authored
  reference, and resolved symbol (or `None` for an entry outside the selected surface).
- `configuration_path`: the configuration owner for target-level diagnostics.

`MODULE` nodes represent execution; `LOCAL` nodes represent local closures and are
traversable but are not subjects of unused-definition diagnostics. Symbol IDs must not
be persisted across snapshots. `matches_symbol_patterns` exposes the configuration glob
grammar for custom root matching. Queries record source and metadata dependencies.

These facts contain neither liveness verdicts nor stale-root results. The FFL106–FFL108
custom-rule exemplars independently match configured roots and traverse these edges,
preserving the native/custom equivalence contract. `RuleCase.config` accepts `dead_code`
for public-harness tests of custom reachability rules.
