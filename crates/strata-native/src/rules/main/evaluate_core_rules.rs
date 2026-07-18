//! Evaluate registered native rules against one parsed program.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::PARAMETER_ANNOTATION_CODE;
use crate::rules::helpers::annotations::parameter_annotation_faults;
use crate::rules::models::NativeFaultRow;

pub fn evaluate_core_rules(program: &ProgramHandle, codes: &[String]) -> Vec<NativeFaultRow> {
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    for code in codes {
        if code == PARAMETER_ANNOTATION_CODE {
            faults.extend(parameter_annotation_faults(program.annotation_rows()));
        }
    }
    faults
}
