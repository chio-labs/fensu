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

Custom-host invocations require an explicit timeout. The transport drains both
output streams while writing the request, terminates an unresponsive process
tree, and validates protocol and runtime identities before returning a payload.
Suppression and ignore paths use canonical repository-relative POSIX text.
