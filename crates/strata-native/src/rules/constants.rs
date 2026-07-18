//! Native rule registrations and their consumed public fact families.

pub const PARAMETER_ANNOTATION_CODE: &str = "SFA001";
pub const NATIVE_RULE_FACT_FAMILIES: &[(&str, &[&str])] =
    &[(PARAMETER_ANNOTATION_CODE, &["annotations"])];
