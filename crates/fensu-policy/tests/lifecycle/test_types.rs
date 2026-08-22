//! Consumer-owned fixture and test-case models.

use std::collections::HashMap;
use std::path::PathBuf;

use fensu_policy::lifecycle::errors::LifecycleError;
use fensu_policy::lifecycle::models::{CustomHostOutputLimits, SkillFreshness};
use fensu_policy::policy::types::PolicyRule;
use serde::{Deserialize, Serialize};

#[derive(Debug)]
pub(crate) struct ConsumerRule {
    pub(crate) code: &'static str,
}

impl PolicyRule for ConsumerRule {
    type Applicability = ();

    fn code(&self) -> &str {
        self.code
    }

    fn enabled_by_default(&self) -> bool {
        true
    }

    fn is_applicable(&self, _applicability: &Self::Applicability) -> bool {
        true
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub(crate) struct ConsumerFacts {
    pub(crate) columns: HashMap<String, String>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct HostPayload {
    pub(crate) hosted: bool,
}

pub(crate) struct ConsumerLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_codes: Vec<&'static str>,
    pub(crate) expected_blocking: usize,
    pub(crate) expected_warnings: usize,
    pub(crate) expected_suppressions: usize,
    pub(crate) expected_scoped_ignores: usize,
    pub(crate) expected_hosted: bool,
    pub(crate) expected_freshness: SkillFreshness,
}

pub(crate) struct CacheLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_invalidated: bool,
    pub(crate) expected_removed: bool,
}

pub(crate) struct ErrorLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_error: LifecycleError,
}

pub(crate) struct SkillLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_stale: SkillFreshness,
    pub(crate) expected_divergent: SkillFreshness,
    pub(crate) expected_missing: SkillFreshness,
}

pub(crate) struct IdentityLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_unique_identities: usize,
}

pub(crate) struct OrderedIdentityLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_schema: u32,
    pub(crate) expected_distinct: bool,
}

pub(crate) struct SuppressionMatchLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_suppressions: usize,
    pub(crate) expected_scoped_ignores: usize,
    pub(crate) expected_findings: usize,
    pub(crate) expected_symbol: &'static str,
}

pub(crate) struct SerializationLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_equal: bool,
}

#[cfg(unix)]
pub(crate) struct HostLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_payload: bool,
}

pub(crate) struct HostOverflowLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) command: fn() -> (PathBuf, Vec<String>),
    pub(crate) output_limits: CustomHostOutputLimits,
    pub(crate) expected_error: LifecycleError,
}

pub(crate) struct HostResponseLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) response: &'static str,
    pub(crate) expected_error: LifecycleError,
}

pub(crate) struct SuccessfulProcessTreeLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_payload: bool,
    pub(crate) expected_stopped: bool,
}

pub(crate) struct ProcessTreeLifecycleTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_stopped: bool,
}
