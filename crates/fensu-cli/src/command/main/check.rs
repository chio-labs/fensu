use crate::check::main::execute_check::execute_check;
use crate::models::CliOutput;

pub(crate) fn run(
    arguments: &[String],
    target_names: Option<&std::collections::HashSet<String>>,
) -> Result<CliOutput, String> {
    execute_check(arguments, target_names)
}
