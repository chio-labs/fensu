//! Rule catalogue transport models shared by the build and runtime crates.

use serde::{Deserialize, Serialize};

use crate::analyzer::AnalyzerId;

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RuleMetadata {
    pub(crate) code: String,
    pub(crate) family: String,
    pub(crate) slug: String,
    pub(crate) message: String,
    pub(crate) remediation: Option<String>,
    pub(crate) severity: String,
    pub(crate) enabled_by_default: bool,
    pub(crate) analyzers: Vec<AnalyzerId>,
    pub(crate) execution_owner: String,
    pub(crate) kind: String,
    #[serde(default)]
    pub(crate) pack: Option<String>,
    #[serde(default)]
    pub(crate) alias_of: Option<String>,
    #[serde(default)]
    pub(crate) implementation_code: Option<String>,
    #[serde(default)]
    pub(crate) source: Option<String>,
    #[serde(default)]
    pub(crate) cacheable: Option<bool>,
    #[serde(default)]
    pub(crate) options: Vec<RuleOptionMetadata>,
    #[serde(default)]
    pub(crate) constraints: Vec<RuleConstraintMetadata>,
    #[serde(default)]
    pub(crate) thresholds: Vec<String>,
    #[serde(default)]
    pub(crate) contract_behaviors: Vec<String>,
    #[serde(default)]
    pub(crate) configuration_inputs: Vec<String>,
    #[serde(default)]
    pub(crate) limits: Vec<RuleLimitMetadata>,
}

impl fensu_policy::policy::types::PolicyRule for RuleMetadata {
    type Applicability = AnalyzerId;

    fn code(&self) -> &str {
        &self.code
    }

    fn enabled_by_default(&self) -> bool {
        self.enabled_by_default
    }

    fn is_applicable(&self, applicability: &Self::Applicability) -> bool {
        self.analyzers.contains(applicability)
    }

    fn implementation_code(&self) -> &str {
        self.alias_of.as_deref().unwrap_or(&self.code)
    }
}

#[derive(Debug)]
pub(crate) struct SelectorValidationRequest<'a> {
    pub(crate) name: &'a str,
    pub(crate) selectors: &'a [String],
    pub(crate) applicable: &'a [&'a RuleMetadata],
    pub(crate) configured: &'a [&'a RuleMetadata],
    pub(crate) analyzer: &'a AnalyzerId,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RuleConstraintMetadata {
    pub(crate) name: String,
    pub(crate) description: String,
    pub(crate) values: Vec<String>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RuleLimitMetadata {
    pub(crate) name: String,
    pub(crate) description: String,
    pub(crate) value: u32,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RuleOptionMetadata {
    pub(crate) name: String,
    pub(crate) kind: String,
    pub(crate) required: bool,
    pub(crate) default: Option<RuleOptionValue>,
    pub(crate) current_value: RuleOptionValue,
    pub(crate) description: Option<String>,
    pub(crate) choices: Option<Vec<String>>,
    pub(crate) minimum: Option<i64>,
    pub(crate) maximum: Option<i64>,
    pub(crate) minimum_items: Option<usize>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(untagged)]
pub(crate) enum RuleOptionValue {
    Boolean(bool),
    Integer(i64),
    String(String),
    List(Vec<RuleOptionListValue>),
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(untagged)]
pub(crate) enum RuleOptionListValue {
    Integer(i64),
    String(String),
}
