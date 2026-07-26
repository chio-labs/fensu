use crate::command::helpers::memory::execution::execute_memory;
use crate::models::CliOutput;

pub(crate) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    execute_memory(arguments)
}
