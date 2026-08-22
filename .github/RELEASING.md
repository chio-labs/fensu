# Release Automation

Fensu uses Release Please and conventional commits to maintain the release pull request,
version files, and `CHANGELOG.md`. Merging an ordinary conventional change into `main`
starts the trusted release workflow.

## Trusted Release Flow

1. Release Please creates or updates its generated release pull request.
2. The workflow checks out that exact release branch and refreshes `uv.lock` and
   `Cargo.lock` when synchronized package versions change.
3. The workflow dispatches pull-request metadata and version guard against the exact
   release head SHA. It reuses `Verify` only after proving the release base tree matches
   the successfully verified head of that specific merged pull request. Trusted code from
   that base checks every owned manifest and lockfile version before and after lock refresh.
4. Only after every trusted check passes, the workflow squash-merges the release pull
   request and dispatches Release Please on `main` again.
5. Release Please creates the GitHub `v0*` release. The workflow dispatches `publish.yml`
   for that exact tag.
6. Publish builds every supported native wheel plus both source distributions, validates
   the standalone CLI wheel tags, publishes through PyPI trusted publishing, and publishes
   the shared Rust crates through crates.io trusted publishing.

The publish workflow is dispatch-only so creating a GitHub release cannot race a second
publication run.

## Repository Configuration

The GitHub repository must provide:

- A `pypi` environment approved for trusted publishing.
- PyPI trusted publishers for the `fensu` and `fensu-cli` distributions using
  `.github/workflows/publish.yml` and the `pypi` environment.
- A `crates-io` environment and crates.io trusted publishers for `fensu-policy` and
  `fensu-structure-checker` using `.github/workflows/publish.yml`. An owner must publish
  each new crate once before crates.io allows its trusted publisher to be configured.
- Workflow permissions that allow Release Please to write contents, pull requests,
  actions, and commit statuses as declared in the workflow.
- Branch protection requiring `Pull Request Metadata`, `Block automatic 1.0 releases`,
  and `Verify` for ordinary pull requests.

Automatic releases remain restricted to `v0*`. Crossing to `1.0.0` requires an explicit
manual decision and corresponding version-guard change.

## Pull Requests

Non-automated branches and titles use Conventional Commits types. Pull request bodies
must contain these non-empty sections in order:

```markdown
## Why

## Changes

## Verification
```

Generated Release Please branches are exempt from the manual body format, but their
titles must still follow Conventional Commits.
