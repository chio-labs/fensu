# fensu-policy

`fensu-policy` provides product-neutral rule-code grammar, selector validation,
applicability filtering, policy-tier resolution, and implementation identity
validation. Consumers project their own rule metadata onto the `PolicyRule`
trait, so the crate has no dependency on Fensu analyzers or product models.

Use `FensuRuleCodeGrammar` for `FF`, `FP`, and `X` rules. Product adapters use
`ProductRuleCodeGrammar`, for example `("SQBK", "XSQBK")` or
`("STBK", "XSTBK")`, while retaining the same selection and tier semantics.
`resolve_policy` rejects duplicate active implementation identities for
execution. Metadata-only catalogue views that intentionally retain aliases use
`resolve_catalogue_policy`.

The `lifecycle` module supplies the remaining reusable execution contracts:
versioned capability-negotiated analysis batches, cache identities and storage,
exact stale-checked suppressions, path-scoped ignores, deterministic finding
serialization and report counts, generated-skill freshness, and an isolated
custom-host request/response protocol. Facts and evaluators remain consumer
owned, so product adapters do not import Fensu CLI internals.

Custom-host invocations require an explicit timeout and explicit
`CustomHostOutputLimits` for stdout and stderr. Each capture stays within its
configured byte bound; overflow returns `LifecycleError::HostOutputOverflow`
with the stream and limit. The transport drains both streams while writing the
request, observes the process leader, and unconditionally terminates and reaps
the remaining process group or Windows Job Object after leader exit. A valid
response has a non-empty matching runtime version and exactly one of a payload
or a non-empty error. The custom-host wire protocol remains version 1.
On Windows, the Job Object is also configured to terminate on handle drop. On
Unix, cleanup covers the launched process group; a deliberately hostile host
that creates a new session can escape that process group, so custom hosts are
trusted plugins rather than an operating-system sandbox.

Batch cache identities use `CACHE_IDENTITY_SCHEMA_VERSION` 2. Required and
supported capabilities retain set semantics, while analysis input order is
identity-significant. The separate on-disk cache envelope remains schema 1;
the changed identity naturally invalidates results produced by the old
order-insensitive algorithm.

Generated skills use ownership schema 2 and include an explicit owner as well
as the skill identity and input/content fingerprints. `render_owned_skill` and
`skill_freshness` therefore both take `owner` and `identity`. Schema-v1 markers
are recognized as `SkillFreshness::Unowned`, as are schema-v2 markers belonging
to another owner. For matching owners, edited content is `Divergent` even when
its inputs are also stale, preventing regeneration from hiding local edits.

Suppression and ignore paths use canonical repository-relative POSIX text.
`apply_suppressions` validates finding and evaluated rule codes as exact codes
and validates all finding paths before matching. Exact suppressions are indexed,
selector matches are indexed by incoming finding code, and scoped path globs are
compiled once per call rather than once per finding.
