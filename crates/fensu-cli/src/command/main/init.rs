use crate::init::main::run_init::run_init;
use crate::models::CliOutput;

pub(super) fn init(arguments: &[String]) -> Result<CliOutput, String> {
    run_init(arguments)
}
