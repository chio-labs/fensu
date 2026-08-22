//! Consumer-owned types used to prove the public policy contract.

use fensu_policy::policy::errors::PolicyError;
use fensu_policy::policy::models::PolicySelectors;
use fensu_policy::policy::types::PolicyRule;

pub(crate) struct ValidationTestCase {
    pub(crate) description: &'static str,
    pub(crate) value: &'static str,
    pub(crate) expected_valid: bool,
}

pub(crate) struct SelectorValidationTestCase {
    pub(crate) description: &'static str,
    pub(crate) selector: &'static str,
    pub(crate) expected_error: PolicyError,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SqlDialect {
    Postgres,
    Snowflake,
}

#[derive(Debug)]
pub(crate) struct SqlRule {
    pub(crate) code: &'static str,
    pub(crate) enabled: bool,
    pub(crate) dialects: &'static [SqlDialect],
    pub(crate) implementation: Option<&'static str>,
}

pub(crate) struct SqlPolicyTestCase {
    pub(crate) description: &'static str,
    pub(crate) rules: Vec<SqlRule>,
    pub(crate) dialect: SqlDialect,
    pub(crate) selectors: PolicySelectors,
    pub(crate) expected_catalogue: Vec<&'static str>,
    pub(crate) expected_blocking: Vec<&'static str>,
    pub(crate) expected_warnings: Vec<&'static str>,
    pub(crate) expected_ignored: Vec<&'static str>,
    pub(crate) expected_error: Option<PolicyError>,
}

pub(crate) struct ImplementationIdentityTestCase {
    pub(crate) description: &'static str,
    pub(crate) rules: Vec<SqlRule>,
    pub(crate) expected_error: PolicyError,
}

impl PolicyRule for SqlRule {
    type Applicability = SqlDialect;

    fn code(&self) -> &str {
        self.code
    }

    fn enabled_by_default(&self) -> bool {
        self.enabled
    }

    fn is_applicable(&self, applicability: &Self::Applicability) -> bool {
        self.dialects.contains(applicability)
    }

    fn implementation_code(&self) -> &str {
        self.implementation.unwrap_or(self.code)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum StreamMode {
    Batch,
    Continuous,
}

#[derive(Debug)]
pub(crate) struct StreamRule {
    pub(crate) code: &'static str,
    pub(crate) mode: StreamMode,
}

pub(crate) struct StreamPolicyTestCase {
    pub(crate) description: &'static str,
    pub(crate) rules: Vec<StreamRule>,
    pub(crate) mode: StreamMode,
    pub(crate) selectors: PolicySelectors,
    pub(crate) expected_catalogue: Vec<&'static str>,
    pub(crate) expected_blocking: Vec<&'static str>,
}

impl PolicyRule for StreamRule {
    type Applicability = StreamMode;

    fn code(&self) -> &str {
        self.code
    }

    fn enabled_by_default(&self) -> bool {
        true
    }

    fn is_applicable(&self, applicability: &Self::Applicability) -> bool {
        self.mode == *applicability
    }
}
