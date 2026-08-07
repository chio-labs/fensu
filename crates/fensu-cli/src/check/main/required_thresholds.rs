//! Thresholds the given rule codes require.

use std::collections::HashSet;

pub(crate) fn required_thresholds(codes: &[String]) -> Result<HashSet<&'static str>, String> {
    crate::check::_helpers::rule_policy::required_thresholds(codes)
}
