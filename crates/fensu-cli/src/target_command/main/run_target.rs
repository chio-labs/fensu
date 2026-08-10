use std::env;

use crate::models::CliOutput;
use crate::target_command::_helpers::{addition, arguments};
use crate::target_command::constants::HELP;

pub(crate) fn run_target(arguments: &[String]) -> Result<CliOutput, String> {
    if arguments
        .iter()
        .any(|value| matches!(value.as_str(), "--help" | "-h"))
    {
        return Ok(CliOutput::success(HELP.to_owned()));
    }
    let request = arguments::parse(arguments)?;
    let repository = env::current_dir().map_err(|error| error.to_string())?;
    addition::add_target(&repository, &request)?;
    Ok(CliOutput::success(format!(
        "Added target {} (analyzer=svelte, root={}, roots=src, tests=, tooling=, test_layout=mirrored, packs=) to fensu.toml\n",
        request.name, request.path
    )))
}
