//! Structured failures returned by generic policy validation.

use std::fmt;

use crate::policy::types::PolicyTier;

/// Consumer-neutral policy configuration failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PolicyError {
    InvalidSelector {
        group: String,
        selector: String,
    },
    SelectorMatchesNoConfiguredRule {
        group: String,
        selector: String,
    },
    SelectorMatchesOnlyInapplicableRules {
        group: String,
        selector: String,
        exact: bool,
    },
    TierConflict {
        code: String,
        first: PolicyTier,
        second: PolicyTier,
    },
    DuplicateImplementation {
        first_code: String,
        second_code: String,
        implementation_code: String,
    },
}

impl fmt::Display for PolicyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{self:?}")
    }
}

impl std::error::Error for PolicyError {}
