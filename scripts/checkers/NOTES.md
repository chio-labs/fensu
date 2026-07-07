# scripts/checkers — vendored checker scaffold (THROWAWAY)

Temporary scaffold per .ai/12 Phase 0 + D10 (as amended). Enforces structure/
testing/annotation conventions on strata's own code — INCLUDING this checker
code itself (scripts/ is inside the enforced scope; the enforcer is enforced) —
while strata is built. DELETED at the Phase 6 self-hosting cutover (`make
check` body swaps to `strata check src/strata`).

## Location (SECOND AMENDMENT, user-directed 2026-07-07)

Originally vendored into `_bootstrap/` per D10's "clearly-temporary location".
Moved to `scripts/checkers/` immediately after: the repo must have its enforcer
living in the repo's real tooling home, inside the checked scope, from the
start (sqlbuild parity — its checkers live in scripts/ and check themselves).
Mirrored tests moved to `tests/unit/scripts/checkers/...` so the testing
checker's own mirroring rules (TC030/034/035) pass on them.

## Provenance (FIRST AMENDMENT to the original D10 plan)

Vendored from the CURRENT sqlbuild checkers (scripts/structure, scripts/testing,
scripts/type_annotations @ sqlbuild repo, 2026-07-07), NOT from checkers.zip.
Reason: the zip trust audit (.ai/15-zip-vs-sqlbuild-audit.md) found the zip
missing the entry-shape caps (SC019/020/026), the whole SC063-068 shape/phase
family, TC015(real)/016/022, with ~15 further weakened rules and thinned tests.
The zip's LAYOUT (checkers/<name>/ under one folder) was kept; sqlbuild's RULES
were kept. User-ratified 2026-07-07.

## Patches applied to the sqlbuild source (all deliberate)

- imports `scripts.*` -> `scripts.checkers.*`; entry scripts anchor sys.path at
  the repo root (parents[3]).
- position anchors: `("src","sqlbuild")` -> `_RUNTIME_PREFIX = ("src","strata")`
  (+ `_RUNTIME_PACKAGE_NAME`, `_RUNTIME_PREFIX_TEXT` constants in rules.py).
- REMOVED domain-specific rules (stay in sqlbuild; future custom-rule examples):
  SC023/024/025/031/032/037/038/040/041/042/045/051/052/053/054/057/058/062.
- REMOVED sqlbuild-specific carve-outs inside kept rules: spec/adapter domain
  exemptions (SC033), adapters/integrations/client/orchestration exemptions
  (SC027/SC006/SC019-026 entry shape), integrations helpers __all__ exemption
  (SC047), integrations re-export allowance (SC046), providers.py allowance
  (SC018), SC048 path allowlist, testing checker's sqlbuild/providers mirroring
  carve-out (TC033).
- SC067 scope gate generalized: compiler/executor helpers -> ANY runtime
  helpers/ module (`_is_runtime_helpers_module`).
- SC035/036 messages generalized ("structured SQLBuild error" -> project error).
- ADDED (zip-derived, scaffold codes SC9xx to avoid colliding with sqlbuild
  numbering): SC901 no-runtime-imports-from-scripts; SC902-905 thin scripts/
  entrypoint shape (line cap 80; only main()/parse_args(); no classes; no
  module-level collection constants) — applies to DIRECT children of scripts/
  only. Adapted from the zip's bin-entrypoint rule (SC039-044 zip numbering);
  the "must import runtime package / call runtime main entrypoint" halves were
  dropped (bin/ = runtime CLIs; scripts/ = dev tooling that may be standalone).
- ADDED SC906 no-shared-packages (strata decision, 00-overview #8; sqlbuild
  will adopt the ban when it adopts strata): ANY file under a shared/ segment
  in the runtime package is flagged. sqlbuild's shared/ rules (SC012/SC013) and
  the shared allowances inside the import rules are KEPT verbatim (they are
  correct while a shared/ dir momentarily exists, and keep the diff-vs-sqlbuild
  minimal) — SC906 bans the directory itself, making them unreachable in a
  compliant tree. Remediation MESSAGES that taught shared/ as the fix were
  rewritten (SC011 "promote to shared/" -> "publish via main/ or role files";
  SC033 "...or shared/" -> "publish via main/"; SC017 "subpackage or shared/"
  -> "subpackage") so agents reading checker output during the build are never
  steered toward the banned pattern. Codes and detection logic unchanged.

## Consequence for strata's own tests during bootstrap

The vendored testing checker enforces sqlbuild's mirroring: src-backed tests
live under `tests/unit/src/strata/<area>/...` (TC031), NOT `tests/unit/strata/`
as an early draft of the plan said. Phase 1+ tests follow TC031 while the
scaffold rules; this also matches where strata's own SFT family will want them
(mirror the declared root path).

## Ground mapping (Phase 0 exit check)

- Authoritative rule source = sqlbuild repo scripts/*/... CONFIRMED.
- SC/TC/TA deltas vs the zip: recorded in .ai/15-zip-vs-sqlbuild-audit.md
  (supersedes the code-number delta in .ai/07; the zip renumbered codes).
- tests/unit/scripts/checkers/ = sqlbuild's mirrored checker tests, adapted:
  src/sqlbuild -> src/strata fixtures, domain-rule cases dropped (27),
  shared-main case now also expects SC027 (carve-out removed), new cases for
  SC901-905. 125 pass.

## Running

- `make check` — the three checkers against src/strata + scripts + tests.
- `make test` — pytest on tests/ (includes the vendored checker tests).
- `make verify` — both. All green as of Phase 0 exit; self-check proven by
  mutation (violation injected into checker code itself is flagged).
