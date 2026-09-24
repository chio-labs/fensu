use crate::dupes::main::run_dupes::run_dupes;
use crate::models::CliOutput;

pub(super) fn run(arguments: &[String]) -> Result<CliOutput, String> {
    run_dupes(arguments)
}
