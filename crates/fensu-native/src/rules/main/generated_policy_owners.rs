//! Public inspection of generated fixed-policy ownership.

pub fn generated_policy_owners() -> &'static [&'static str] {
    crate::rules::_helpers::generated_policy::GENERATED_POLICY_OWNERS
}
