//! Run one check and render its report.

use crate::check::_helpers::execution::{cached_output, render_check};
use crate::check::_helpers::options::{parse_options, requests_help};
use crate::check::_helpers::preparation::prepare_checks;
use crate::check::constants::CHECK_HELP;
use crate::models::CliOutput;

pub(crate) fn execute_check(
    arguments: &[String],
    target_names: Option<&std::collections::HashSet<String>>,
) -> Result<CliOutput, String> {
    if requests_help(arguments) {
        return Ok(CliOutput::success(CHECK_HELP.to_owned()));
    }
    let options = parse_options(arguments)?;
    let plan = prepare_checks(&options, target_names)?;
    if let Some(cached) = cached_output(&plan, &options) {
        return Ok(cached);
    }
    render_check(plan, &options)
}
