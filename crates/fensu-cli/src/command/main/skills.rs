use crate::models::CliOutput;

pub(super) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    crate::skills::main::skills::run(arguments)
}
