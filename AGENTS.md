# Repository Agent Instructions

## Testing

- Run focused Python tests with explicit file paths or node IDs and xdist:
  `uv run pytest <paths> -q -n auto --dist loadfile`.
- Run focused Rust tests by package and, where practical, by test target:
  `cargo test -p <package> [--test <target>]`.
- Run focused formatting, lint, type, catalogue, and structure checks for touched files and affected
  boundaries before pushing.
- `make verify`, `make test`, `make test-rust`, cross-platform smoke tests, source builds,
  performance checks, and publication checks are broad CI gates. Do not rerun them locally unless
  reproducing a specific failure, CI is unavailable, or the user explicitly requests it.
- GitHub CI is the authoritative broad-suite gate. Do not delay a ready push to duplicate expensive
  checks that CI already owns.

## Delivery Workflow

- Consolidate related work targeting the same release into one delivery branch and one pull
  request. Use separate pull requests only for independently releasable work, intentionally
  different delivery timing, concrete risk isolation, or explicit user instruction.
- Local commits do not trigger CI. Complete implementation, focused verification, and local review
  before the first push. Do not push partial or overlapping branches merely to start CI.
- Review the complete local diff against `origin/main` and resolve findings before pushing.
- Push one ready change and open one ready pull request. Enable auto-merge and do not manually merge
  while automation is healthy.
- Branches must use `<type>/<kebab-case>` or `<type>/chi-<number>-<kebab-case>`. Pull request titles
  must follow Conventional Commits. Pull request descriptions must be at most 2,000 characters and
  contain non-empty `## Why`, `## Changes`, and `## Verification` sections in that order.
- Monitor CI after every push and address failures before considering delivery complete. Push
  follow-up commits only for CI failures or correctness findings that could not reasonably have
  been found before the first push.
- For releasable changes, continue through auto-merge, Release Please, package publication, and
  verification of the published PyPI and crates.io versions. Do not stop at pull request creation
  unless the user explicitly asks.
- Never deploy or dispatch a publication workflow manually without explicit user authorization.

## Bounded Review Process

1. Perform one targeted local diff scan of dangerous seams: analyzer routing, selector gates, cache
   identities, diagnostics, exit codes, generated catalogue assets, and release metadata.
2. Run exactly one independent read-only review pass over the complete combined diff. Require
   file-and-line evidence for concrete correctness, data-loss, authorization, or behavioral
   regression findings; do not request architecture expansion.
3. Validate findings against supported behavior. Fix validated in-scope bugs and escalate changes
   that would expand behavior, permissions, operational cost, or ownership.
4. If fixes are made, run one follow-up pass limited to those findings and affected boundaries.
   Never restart a broad review loop.
5. Use focused local checks and repository CI as the final arbiters after the bounded review cycle.

## Public Repository Hygiene

- Treat every tracked file, fixture, example, commit, branch, pull request, and release as public.
- Use neutral public examples and run the configured private public-repository hygiene scanner
  against the repository before the first push.
- Never bypass configured Git hooks or publish when the private hygiene scanner is unavailable or
  failing.
