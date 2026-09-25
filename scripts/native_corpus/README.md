# Native diagnostic corpus capture

The per-file capture plugin records native execution requests, project source planes,
filesystem snapshots, observation answers, and expected diagnostic rows. Directory and
project-observation rules retain those inputs even though their request has a source anchor.

Typed project reachability rules run outside the per-file batch API. The plugin also captures
their actual selected source snapshots, module identities, configured root patterns, exact
entry-point references, configuration diagnostic path, and returned faults. Rust reparses the
sources and evaluates the ordinary native rule dispatcher; it does not replay a captured
reachability verdict.

`project_rules.jsonl` is a generated supplement shared by the legacy and current corpus
contracts. Both combined corpora must still request every registered core rule, and both
compare every expected diagnostic exactly. The original per-file fixture files remain intact.

Regenerate only the project supplement with:

```sh
make native-project-corpus-generate
```

This runs the canonical parity fixtures and the synthetic reachability scenarios with xdist.
Workers transfer JSON records to the controller, which writes one deterministically sorted
file after successful tests. `FENSU_CORE_FIXTURE_OUTPUT` selects the per-file output;
`FENSU_CORE_PROJECT_FIXTURE_OUTPUT` independently selects the project output. Omit either
variable to preserve that corpus. The broader `native-corpus-generate` target writes both.

The retained FFR306 per-file fixture predates additional grouping/domain discovery probes.
Current capture adds parent `directory_entries`, domain `glob`, and domain `is_dir` answers;
its source and expected diagnostics are unchanged. Those unrelated observation changes are
not part of the project-capture update.
