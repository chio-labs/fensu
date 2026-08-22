//! Public extension traits and policy categories.

/// Consumer-owned rule metadata projected onto generic policy behavior.
pub trait PolicyRule {
    type Applicability: ?Sized;

    fn code(&self) -> &str;

    fn enabled_by_default(&self) -> bool;

    fn is_applicable(&self, applicability: &Self::Applicability) -> bool;

    fn implementation_code(&self) -> &str {
        self.code()
    }
}

/// Consumer-owned rule-code and selector grammar.
pub trait RuleCodeGrammar {
    fn rule_code_is_exact(&self, value: &str) -> bool;

    fn rule_selector_is_valid(&self, value: &str) -> bool;

    fn code_matches_selector(&self, code: &str, selector: &str) -> bool {
        self.rule_code_is_exact(code)
            && self.rule_selector_is_valid(selector)
            && code.starts_with(selector)
    }
}

/// Mutually exclusive resolved policy tiers.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PolicyTier {
    Blocking,
    Warning,
    Ignored,
}
