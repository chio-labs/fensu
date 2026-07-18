//! Native rule registrations and their consumed public fact families.

pub const PARAMETER_ANNOTATION_CODE: &str = "SFA001";
pub const RETURN_ANNOTATION_CODE: &str = "SFA002";
pub const MODULE_VARIABLE_ANNOTATION_CODE: &str = "SFA101";
pub const CLASS_ATTRIBUTE_ANNOTATION_CODE: &str = "SFA102";
pub const LOCAL_VARIABLE_ANNOTATION_CODE: &str = "SFA103";
pub const NATIVE_RULE_FACT_FAMILIES: &[(&str, &[&str])] = &[
    (PARAMETER_ANNOTATION_CODE, &["annotations"]),
    (RETURN_ANNOTATION_CODE, &["annotations"]),
    (MODULE_VARIABLE_ANNOTATION_CODE, &["annotations"]),
    (CLASS_ATTRIBUTE_ANNOTATION_CODE, &["annotations"]),
    (LOCAL_VARIABLE_ANNOTATION_CODE, &["annotations"]),
];
