use crate::command::constants::MAP_HELP;
use crate::command::helpers::map_parsing;
use crate::mapping::main::map;
use crate::models::CliOutput;

pub(crate) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    match map_parsing::parse(arguments)? {
        Some(options) => map::execute(options),
        None => Ok(CliOutput::success(MAP_HELP.to_owned())),
    }
}
