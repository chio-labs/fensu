use crate::command::_helpers::memory::execution::execute_memory;
use crate::models::CliOutput;

pub(super) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    execute_memory(arguments)
}
