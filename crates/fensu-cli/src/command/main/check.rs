use crate::helpers::check_execution::execute_check;
use crate::models::CliOutput;

pub(crate) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    execute_check(arguments)
}
