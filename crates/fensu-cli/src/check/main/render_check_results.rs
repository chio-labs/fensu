//! Render one aggregate set of analyzer check results.

use std::path::Path;

use crate::check::models::CheckResult;

pub(crate) fn render_check_results(
    results: Vec<CheckResult>,
    root: &Path,
    color: bool,
    show_warnings: bool,
) -> (String, i32) {
    crate::check::_helpers::evaluation::render_results(results, root, color, show_warnings)
}
