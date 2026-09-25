//! Evaluate project reachability even when no source remains to anchor a file batch.

use crate::rules::models::{NativeDeadCodeContext, NativeFaultRow, NativeProjectPlane};

pub fn evaluate_dead_code(
    codes: &[String],
    context: &NativeDeadCodeContext,
    project: &NativeProjectPlane,
) -> Vec<NativeFaultRow> {
    crate::rules::_helpers::dead_code::faults(codes, context, project)
}
