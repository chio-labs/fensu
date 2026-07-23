//! Evaluate registered native rules against one parsed program.

use fensu_facts::extension::models::ProgramHandle;

use crate::rules::constants::{
    CLASS_ATTRIBUTE_ANNOTATION_CODE, LOCAL_VARIABLE_ANNOTATION_CODE,
    MODULE_VARIABLE_ANNOTATION_CODE, NATIVE_RULE_OPTIONS, PARAMETER_ANNOTATION_CODE,
    RETURN_ANNOTATION_CODE,
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
use crate::rules::models::{NativeFaultRow, NativeProjectPlane, NativeRuleContext};

pub fn evaluate_core_rules(
    program: &ProgramHandle,
    codes: &[String],
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Result<Vec<NativeFaultRow>, String> {
    validate_rule_options(codes, context)?;
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
                } else if let Some(rule_faults) = layer_faults(program, code, context, project) {
                    faults.extend(rule_faults);
                } else if let Some(rule_faults) = role_faults(program, code, context) {
                    faults.extend(rule_faults);
                } else if let Some(rule_faults) = test_faults(program, code, context) {
                    faults.extend(rule_faults);
                }
            }
        }
    }
    Ok(faults)
}

fn validate_rule_options(codes: &[String], context: &NativeRuleContext) -> Result<(), String> {
    for (code, values) in &context.rule_options {
        if !codes.contains(code) {
            return Err(format!(
                "Native options supplied for unselected rule {code}."
            ));
        }
        let declared = NATIVE_RULE_OPTIONS
            .iter()
            .find_map(|(candidate, names)| (*candidate == code).then_some(*names))
            .unwrap_or_default();
        if let Some(name) = values
            .keys()
            .find(|name| !declared.contains(&name.as_str()))
        {
            return Err(format!(
                "Native rule {code} does not declare option {name}; option was not ignored."
            ));
        }
    }
    Ok(())
}
