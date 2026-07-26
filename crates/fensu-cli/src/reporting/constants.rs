//! ANSI styling and layout constants for rendered reports.

pub(crate) const ORANGE: &str = "\x1b[1;38;5;208m";
pub(crate) const GREEN: &str = "\x1b[1;32m";
pub(crate) const DIM: &str = "\x1b[2m";
pub(crate) const RESET: &str = "\x1b[0m";
pub(crate) const REPORT_LINE_WIDTH: usize = 100;
pub(crate) const HELP_CONTINUATION: &str = "          ";
