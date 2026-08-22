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
