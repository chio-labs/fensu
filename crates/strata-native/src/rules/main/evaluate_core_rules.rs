//! Evaluate registered native rules against one parsed program.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::{
    CLASS_ATTRIBUTE_ANNOTATION_CODE, LOCAL_VARIABLE_ANNOTATION_CODE,
    MODULE_VARIABLE_ANNOTATION_CODE, PARAMETER_ANNOTATION_CODE, RETURN_ANNOTATION_CODE,
};
use crate::rules::helpers::annotations::{
    class_attribute_annotation_faults, local_variable_annotation_faults,
    module_variable_annotation_faults, parameter_annotation_faults, return_annotation_faults,
};
use crate::rules::helpers::hygiene::hygiene_faults;
use crate::rules::models::NativeFaultRow;

pub fn evaluate_core_rules(
    program: &ProgramHandle,
    codes: &[String],
    scope: &str,
) -> Vec<NativeFaultRow> {
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    for code in codes {
        let rows = program.annotation_rows();
        match code.as_str() {
            PARAMETER_ANNOTATION_CODE => faults.extend(parameter_annotation_faults(rows)),
            RETURN_ANNOTATION_CODE => faults.extend(return_annotation_faults(rows)),
            MODULE_VARIABLE_ANNOTATION_CODE => {
                faults.extend(module_variable_annotation_faults(rows));
            }
            CLASS_ATTRIBUTE_ANNOTATION_CODE => {
                faults.extend(class_attribute_annotation_faults(rows));
            }
            LOCAL_VARIABLE_ANNOTATION_CODE => {
                faults.extend(local_variable_annotation_faults(rows));
            }
            _ => {
                if let Some(rule_faults) = hygiene_faults(program, code, scope) {
                    faults.extend(rule_faults);
                }
            }
        }
    }
    faults
}
