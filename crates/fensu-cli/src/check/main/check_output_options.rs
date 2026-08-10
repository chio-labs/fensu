//! Resolve aggregate output behavior from check arguments.

use crate::check::models::CheckOutputOptions;

pub(crate) fn check_output_options(arguments: &[String]) -> Result<CheckOutputOptions, String> {
    let options = crate::check::_helpers::options::parse_options(arguments)?;
    Ok(CheckOutputOptions {
        color: crate::check::_helpers::options::use_color(&options.color),
        show_warnings: options.warn,
        show_cache_stats: options.cache_stats,
    })
}
