//! Rule catalogue transport models shared by the build and runtime crates.

use serde::{Deserialize, Serialize};

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
    pub(crate) execution_owner: String,
    pub(crate) kind: String,
    #[serde(default)]
    pub(crate) pack: Option<String>,
    #[serde(default)]
    pub(crate) alias_of: Option<String>,
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
