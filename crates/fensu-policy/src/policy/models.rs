//! Public policy input and output models.

use crate::policy::constants;
use crate::policy::main::{rule_code_is_exact, rule_selector_is_valid};
use crate::policy::types::RuleCodeGrammar;

/// Fensu's core, pack, and custom rule namespace grammar.
#[derive(Clone, Copy, Debug, Default)]
pub struct FensuRuleCodeGrammar;

impl RuleCodeGrammar for FensuRuleCodeGrammar {
    fn rule_code_is_exact(&self, value: &str) -> bool {
        rule_code_is_exact::rule_code_is_exact(value)
    }

    fn rule_selector_is_valid(&self, value: &str) -> bool {
        rule_selector_is_valid::rule_selector_is_valid(value)
    }
}

/// Fixed product namespaces with one family letter and three numeric digits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProductRuleCodeGrammar {
    built_in_namespace: String,
    custom_namespace: String,
}

impl ProductRuleCodeGrammar {
    pub fn new(built_in_namespace: &str, custom_namespace: &str) -> Result<Self, String> {
        if !Self::namespace_is_valid(built_in_namespace)
            || !Self::namespace_is_valid(custom_namespace)
            || !custom_namespace.starts_with('X')
            || built_in_namespace == custom_namespace
        {
            return Err("rule namespaces must be distinct ASCII uppercase names and the custom namespace must start with X".to_owned());
        }
        Ok(Self {
            built_in_namespace: built_in_namespace.to_owned(),
            custom_namespace: custom_namespace.to_owned(),
        })
    }

    fn namespace_is_valid(namespace: &str) -> bool {
        !namespace.is_empty()
            && namespace
                .bytes()
                .all(|character| character.is_ascii_uppercase())
    }

    fn code_has_namespace(value: &str, namespace: &str) -> bool {
        let Some(suffix) = value.strip_prefix(namespace) else {
            return false;
        };
        suffix.len() == constants::PRODUCT_CODE_SUFFIX_LENGTH
            && suffix[0..1]
                .bytes()
                .all(|character| character.is_ascii_uppercase())
            && suffix[1..]
                .bytes()
                .all(|character| character.is_ascii_digit())
    }

    fn selector_has_namespace(value: &str, namespace: &str) -> bool {
        if namespace.starts_with(value) {
            return true;
        }
        let Some(suffix) = value.strip_prefix(namespace) else {
            return false;
        };
        suffix.len() <= constants::PRODUCT_CODE_SUFFIX_LENGTH
            && suffix
                .bytes()
                .next()
                .is_some_and(|character| character.is_ascii_uppercase())
            && suffix[1..]
                .bytes()
                .all(|character| character.is_ascii_digit())
    }
}

impl RuleCodeGrammar for ProductRuleCodeGrammar {
    fn rule_code_is_exact(&self, value: &str) -> bool {
        Self::code_has_namespace(value, &self.built_in_namespace)
            || Self::code_has_namespace(value, &self.custom_namespace)
    }

    fn rule_selector_is_valid(&self, value: &str) -> bool {
        !value.is_empty()
            && (Self::selector_has_namespace(value, &self.built_in_namespace)
                || Self::selector_has_namespace(value, &self.custom_namespace))
    }
}

/// Configured selectors for each policy tier.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct PolicySelectors {
    pub select: Vec<String>,
    pub warn: Vec<String>,
    pub ignore: Vec<String>,
}

/// Applicable catalogue and resolved policy tiers in catalogue order.
#[derive(Debug)]
pub struct PolicySelection<'rules, Rule> {
    pub catalogue: Vec<&'rules Rule>,
    pub blocking: Vec<&'rules Rule>,
    pub warnings: Vec<&'rules Rule>,
    pub ignored: Vec<&'rules Rule>,
}

/// Configured and applicable views used for selector validation.
#[derive(Debug)]
pub struct PolicyCatalogues<'rules, Rule> {
    pub configured: &'rules [&'rules Rule],
    pub applicable: &'rules [&'rules Rule],
}

/// Internal resolved tiers before the applicable catalogue is attached.
#[derive(Debug)]
pub(crate) struct ResolvedTiers<'rules, Rule> {
    pub(crate) blocking: Vec<&'rules Rule>,
    pub(crate) warnings: Vec<&'rules Rule>,
    pub(crate) ignored: Vec<&'rules Rule>,
}
