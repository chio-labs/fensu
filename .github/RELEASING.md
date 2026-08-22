# Release Automation

Fensu uses Release Please and conventional commits to maintain the release pull request,
version files, and `CHANGELOG.md`. Merging an ordinary conventional change into `main`
starts the trusted release workflow.

## Trusted Release Flow

1. Release Please creates or updates its generated release pull request.
2. The workflow checks out that exact release branch and refreshes `uv.lock` and
   `Cargo.lock` when synchronized package versions change.
3. The workflow dispatches pull-request metadata, version guard, and Verify against the
   exact release head SHA and publishes explicit commit statuses for those checks.
4. Only after every trusted check passes, the workflow squash-merges the release pull
   request and dispatches Release Please on `main` again.
5. Release Please creates the GitHub `v0*` release. The workflow dispatches `publish.yml`
   for that exact tag.
6. Publish builds every supported native wheel plus both source distributions, validates
   the standalone CLI wheel tags, and publishes through PyPI trusted publishing.

The publish workflow is dispatch-only so creating a GitHub release cannot race a second
publication run.

## Repository Configuration

The GitHub repository must provide:

- A `pypi` environment approved for trusted publishing.
- PyPI trusted publishers for the `fensu` and `fensu-cli` distributions using
  `.github/workflows/publish.yml` and the `pypi` environment.
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
