//! Report request models.

use std::path::Path;

use crate::models::{Fault, ThresholdUse};

#[derive(Debug)]
pub(crate) struct ReportRequest<'a> {
    pub(crate) faults: &'a [Fault],
    pub(crate) warnings: &'a [Fault],
    pub(crate) root: &'a Path,
    pub(crate) color: bool,
    pub(crate) show_warnings: bool,
    pub(crate) evaluation_summary: Option<&'a str>,
    pub(crate) applied_exceptions: usize,
    pub(crate) threshold_uses: &'a [ThresholdUse],
}
