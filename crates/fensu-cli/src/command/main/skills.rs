use crate::models::CliOutput;

pub(crate) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    crate::skills::main::skills::run(arguments)
}
