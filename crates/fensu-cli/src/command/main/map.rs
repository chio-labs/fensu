use crate::command::_helpers::map::parsing;
use crate::command::constants::MAP_HELP;
use crate::mapping::main::map;
use crate::models::CliOutput;

pub(crate) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    match parsing::parse(arguments)? {
        Some(options) => map::execute(options),
        None => Ok(CliOutput::success(MAP_HELP.to_owned())),
    }
}
