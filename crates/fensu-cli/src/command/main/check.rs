use crate::check::main::execute_check::execute_check;
use crate::models::CliOutput;

pub(super) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    execute_check(arguments)
}
