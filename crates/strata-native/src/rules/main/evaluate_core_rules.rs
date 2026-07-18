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
use crate::rules::helpers::layers::layer_faults;
use crate::rules::helpers::naming::naming_faults;
use crate::rules::helpers::roles::role_faults;
use crate::rules::helpers::shape::shape_faults;
use crate::rules::helpers::tests::test_faults;
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

pub fn evaluate_core_rules(
    program: &ProgramHandle,
    codes: &[String],
    context: &NativeRuleContext,
) -> Result<Vec<NativeFaultRow>, String> {
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    for code in codes {
        match code.as_str() {
            PARAMETER_ANNOTATION_CODE => {
                faults.extend(parameter_annotation_faults(program.annotation_rows()));
            }
            RETURN_ANNOTATION_CODE => {
                faults.extend(return_annotation_faults(program.annotation_rows()));
            }
            MODULE_VARIABLE_ANNOTATION_CODE => {
                faults.extend(module_variable_annotation_faults(program.annotation_rows()));
            }
            CLASS_ATTRIBUTE_ANNOTATION_CODE => {
                faults.extend(class_attribute_annotation_faults(program.annotation_rows()));
            }
            LOCAL_VARIABLE_ANNOTATION_CODE => {
                faults.extend(local_variable_annotation_faults(program.annotation_rows()));
            }
            _ => {
                if let Some(rule_faults) = naming_faults(program.contract_rows(), code, context) {
                    faults.extend(rule_faults?);
                } else if let Some(rule_faults) = hygiene_faults(program, code, &context.scope) {
                    faults.extend(rule_faults);
                } else if let Some(rule_faults) = shape_faults(program, code, context) {
                    faults.extend(rule_faults);
                } else if let Some(rule_faults) = layer_faults(program, code) {
                    faults.extend(rule_faults);
                } else if let Some(rule_faults) = role_faults(program, code) {
                    faults.extend(rule_faults);
                } else if let Some(rule_faults) = test_faults(program, code) {
                    faults.extend(rule_faults);
                }
            }
        }
    }
    Ok(faults)
}
