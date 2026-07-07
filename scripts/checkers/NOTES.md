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
- STRENGTHENED SC017 (`check_top_level_domain_role_placement`), Phase 1 layout
  decision 2026-07-07: strata bans ALL role placement at the top-level DOMAIN
  level, files AND directories.
  - Role FILE branch: added `exceptions.py` (sqlbuild listed models/types/
    constants/helpers/classes but omitted exceptions.py). Now all six role
    files flag at domain level.
  - Role DIR branch: was `helpers`/`classes` only AND gated on
    `file_path.name == "__init__.py"`. Now covers all six role dir names
    (`_RUNTIME_ROLE_DIRECTORY_NAMES` = helpers/classes/models/types/constants/
    exceptions) and fires on ANY file whose domain-direct-child (relative_parts
    [3]) is a role dir — the `__init__.py` gate is REMOVED.
  - WHY the degate matters: SC017's dir branch only firing on `__init__.py`
    meant deleting `__init__.py` (namespace package) silenced it — an LLM cheat
    vector. Namespace packages under a banned role dir now still flag.
- STRENGTHENED SC030 (`check_nested_runtime_package_direct_subpackages`), same
  date/decision: was gated on `file_path.name == "__init__.py"`, so a nested
  feature bucket with no `__init__.py` escaped entirely. Rewritten to scan the
  package path and flag ANY file under a non-allowed direct child of a nested
  runtime package (immediate-parent semantics preserved: helpers/ still nests
  exactly one level, i.e. helpers/diff/ ok, helpers/diff/parsing/ flagged).
  `__init__.py` gate REMOVED.
- NOT a loophole (left as-is): SC043 (`check_classes_package_module_shape`)
  excludes `__init__.py` from the exactly-one-class requirement — a correct
  EXCLUSION (an __init__ shouldn't be forced to hold a class), not a silencer.
- SFR3xx PORT REQUIREMENTS (write into the real strata rules): the SFR306/307
  (top-level role placement/direct modules) and SFR305 (nested direct
  subpackages) rules MUST fire on any file under the offending directory, NOT
  gated on `__init__.py`. The scaffold tests
  "reports top-level helpers package without __init__ file",
  "reports top-level {classes,models,types,constants,exceptions} package under
  runtime domain", "reports top-level exceptions role file under runtime
  domain", and "reports nested feature package without __init__ file" are the
  reference cases to port. Mutation-proven 2026-07-07 (reinstating either
  `__init__.py` gate fails these).
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
