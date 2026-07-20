use crate::command::helpers::memory_execution::execute_memory;
use crate::models::CliOutput;

pub(crate) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    execute_memory(arguments)
}
