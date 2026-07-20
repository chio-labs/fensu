use std::env;

use crate::models::CliOutput;
use crate::skills::helpers::context::options;
use crate::skills::main::execute;

pub(crate) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    let options = options::parse_options(arguments)?;
    if options.help {
        return Ok(CliOutput::success(options::HELP.to_owned()));
    }
    if options.global_install && options.install_root.is_some() {
        return Ok(CliOutput::error(
            "--install-root cannot be combined with --global.".to_owned(),
        ));
    }
    if options.check && options.force {
        return Ok(CliOutput::error(
            "--check cannot be combined with --force.".to_owned(),
        ));
    }
    let invocation = env::current_dir().map_err(|error| error.to_string())?;
    execute::execute(&invocation, &options, true)
}
