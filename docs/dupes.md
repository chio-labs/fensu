# Duplicated-code detection

`fensu dupes` reports concrete duplicated code. It is an advisory review aid, not a gate:

- It exits 0 whenever analysis succeeds, whatever it finds.
- It exits 2 for usage errors, invalid configuration, unknown `--since` revisions, and IO failures.
- Unlike `fensu check`, its findings never need to reach zero. Treat each cluster as a hypothesis:
  consolidate genuine copies, and record intentional mirrors in `[dupes]` with a reason.

```sh
fensu dupes                              # top 30 clusters for the whole repository
fensu dupes --since origin/main          # only clusters touching lines changed since a revision
fensu dupes --since origin/main --diff   # plus where the first two copies diverge
fensu dupes --lang rust --top 10 --json
```

## Acting on a duplicate

A genuine duplicate is often the visible symptom of wider drift: a missing shared owner, two
subsystems implementing one concept, logic on the wrong side of a boundary, or copies that have
already diverged. Before consolidating, work out why the copy exists, use `--diff` to see whether a
fix reached only one copy, and look at neighbouring clusters in the same modules for a larger
pattern. Record that diagnosis before removing the copies: consolidation erases the only
deterministic signal of the underlying drift, which is much harder to find once the duplicate is
gone. Fix the root cause when it is in scope rather than only merging the visible copies.

Before adding helpers or logic to an area, `fensu dupes --path '<area glob>'` shows whether an owner
already exists.

## What is analysed

Sources come from every configured target, discovered exactly as `fensu check` discovers them:
target roots and tooling, with generated paths and `evaluation.include`/`exclude` applied. Configured
test paths, colocated web tests, Rust `tests/` and `benches/` directories, and Rust `#[cfg(test)]`
and `#[test]` items (including `#[cfg(test)] mod name;` files) are skipped unless
`--include-tests` is passed. Paths matching `[dupes] exclude` are skipped.

Units are functions:

- Python: top-level functions and class methods (nested classes qualify as `Outer.Inner.method`),
  parsed with Fensu's Python parser. Decorators are outside the unit.
- Rust: `fn` items with bodies, including impl and trait methods (`Type::method`).
- TypeScript and JavaScript: function declarations, `const name = () => ...` or function
  expressions, and class methods and function-valued properties (`Class.method`).
- Svelte: the same units inside every `<script>` block, with component line numbers.

TypeScript, JavaScript, and Svelte compare with each other; Python and Rust compare within their
own language.

## How similarity works

Each unit becomes a normalised token stream. Local names, parameters, attribute reads, and
literals become placeholders; keywords, operators, and Python layout (newline, indent, dedent)
stay. Call targets keep their names, so two functions with the same layout that call different
helpers are near-misses rather than renamed copies. Comments, docstrings, and type annotations are
dropped.

Candidates come from winnowed 12-token fingerprints (window of 6). Fingerprints shared by more than
25 units are treated as boilerplate. Candidate pairs sharing fingerprints with a Jaccard index of at
least 0.2 are scored with a `difflib`-style matching ratio.

- `exact`: identical tokens after dropping comments, docstrings, and annotations.
- `renamed`: identical normalised streams, so only names and literals differ.
- `near-miss`: ratio at or above `--min-similarity` (default 0.8). When the smaller unit has fewer
  than 80 tokens, a near-miss needs at least 0.9.

Units below `--min-tokens` (default 60) are ignored. Similar pairs join transitive clusters, ranked
by the estimated duplicated tokens: the tokens that would disappear if one copy remained.

## Output

```text
fensu dupes: 2 duplicated-code clusters (advisory; duplicated-code findings to review, not fensu check failures)
analysed python 5 units; 0 allowlisted pairs hidden; 0 contract-exempt members hidden
  1. exact sim 1.00, ~226 duplicated tokens, 3 members
     src/shop/billing/summary.py:1-15 summarize_orders (113 tokens)
     src/shop/orders/summary.py:1-15 summarize_orders (113 tokens)
     src/shop/reports/summary.py:1-15 summarize_orders (113 tokens)
```

Each cluster shows its worst category, similarity range, duplicated-token estimate, and members as
`path:start-end name (tokens)`. `[changed]` marks members touched since the `--since` revision.
`[forced]` marks contract-exempt members (below). `--diff` adds up to 12 differing lines between the
first two members, which are visible (non-forced) members whenever the cluster has two.

`--json` prints the same report as deterministic JSON: `command`, `advisory`, `since`,
`unit_counts`, `allowlisted_pairs`, `contract_exempt_members`, `total_clusters`, and `clusters`.
Each cluster has `rank`, `category`, `similarity_min`, `similarity_max`, `duplicated_tokens`,
`members` (`language`, `path`, `name`, `start_line`, `end_line`, `tokens`, `changed`, `forced`),
`links` between member indexes, and, with `--diff`, `diff` with differing `lines`
(`member`, `line`, `text`) and `omitted_lines`.

| Option | Meaning |
| --- | --- |
| `--top N` | Clusters to print (default 30). |
| `--min-similarity X` | Near-miss threshold in (0, 1] (default 0.8). |
| `--min-tokens N` | Minimum normalised tokens per unit (default 60). |
| `--lang LANG` | `python`, `rust`, `typescript`, `javascript`, or `svelte`; repeatable. |
| `--path GLOB` | Only clusters with a member matching the glob; repeatable. |
| `--include-tests` | Also analyse test code. |
| `--since REV` | Only clusters touching lines added or changed since `REV`, including uncommitted and untracked files. |
| `--diff` | Show where the first two visible members diverge. |
| `--json` | Machine-readable output. |

## Configuration

`[dupes]` sits beside `[targets]` in `fensu.toml`, or under `[tool.fensu.dupes]` in
`pyproject.toml`. It does not affect `fensu check`. Globs use Fensu's path syntax: `*` stays within
one segment, `**` crosses segments, and a pattern without `/` matches a name at any depth.

```toml
[dupes]
exclude = ["scripts/generated/**"]

# A pair is hidden when both members match this entry's paths.
[[dupes.allowlist]]
paths = ["src/shop/exporters/*"]
reason = "Exporters intentionally mirror one partner protocol."

[[dupes.contract_exemptions]]
contract = "src/shop/contract.py:Exporter"
forbidden_owners = ["src/shop/base.py:BaseExporter"]
paths = ["src/shop/exporters/*"]
reason = "The exporter contract test requires every exporter to define each method itself."
```

Every allowlist and contract-exemption entry needs a non-empty `reason`.

### Contract exemptions

Some contracts require every implementation to define a method itself, which produces copies that
must stay. A contract exemption marks those methods `[forced]`:

- The contract methods are the contract class's abstract methods (`@abstractmethod` or
  `@abc.abstractmethod`, including unoverridden inherited ones), read statically from the source.
- A method is forced when its top-level class lies under `paths`, derives from the contract, and
  would otherwise inherit that method from the contract, a `forbidden_owners` class, or nowhere.
- If any class in the method resolution order cannot be resolved inside the repository, the method
  is not forced. This covers classes imported through a package re-export, module-qualified bases
  such as `base.BaseExporter` (including modules of namespace packages without `__init__.py`), and
  bases qualified through a same-file class. Subscripted bases such
  as `BaseExporter[int]` resolve normally, and external or standard-library bases such as `ABC`,
  `Generic[T]`, or `typing` classes never block the exemption.

Links between two forced members are hidden, and clusters left without links disappear; the summary
counts those members as contract-exempt. Links from a forced member to any other unit stay visible,
because a private helper copy or an override that could be inherited is still worth reviewing.
Forced members are listed last and add nothing to the duplicated-token estimate. An entry whose
contract file is absent is inactive; a missing class in an existing file is a configuration error.

Contract exemptions currently apply to Python classes only.
