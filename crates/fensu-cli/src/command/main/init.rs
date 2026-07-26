use crate::helpers::init::run::run_init;
use crate::models::CliOutput;

pub(crate) fn init(arguments: &[String]) -> Result<CliOutput, String> {
    run_init(arguments)
}
