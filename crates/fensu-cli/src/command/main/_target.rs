use crate::models::CliOutput;

pub(super) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    crate::target_command::main::run_target::run_target(arguments)
}
