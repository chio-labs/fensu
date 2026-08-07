# Native Core Rule Corpus

`core_rules.jsonl` is the 531-request legacy corpus introduced by commit
`207a092f6762e460bc451f114b4c3b955143c843` and retained as historical scenario depth.

`generated_rules.jsonl` is generated from the current rule-specific Python suites by
intercepting the native batch request and result boundary. Regenerate it from the
repository root:

```bash
make native-corpus-generate
```

The command runs the rule unit and integration suites sequentially so each request retains its exact pytest node ID,
normalizes temporary repository roots to `<repo-root>`, sorts records deterministically,
and records only `FF` core rules. Rust executes both corpora. It requires every registered
core rule to appear in each corpus and records the small sets of rules whose captured
scenarios are exclusion-only rather than fault-producing.
