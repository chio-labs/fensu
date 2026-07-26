//! Thresholds the given rule codes require.

use std::collections::HashSet;

pub(crate) fn required_thresholds(codes: &[String]) -> HashSet<&'static str> {
    crate::check::_helpers::policy::required_thresholds(codes)
}
