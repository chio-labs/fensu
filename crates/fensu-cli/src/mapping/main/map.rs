use crate::mapping::helpers::execution;
use crate::mapping::models::MapOptions;
use crate::models::CliOutput;

pub(crate) fn execute(options: MapOptions) -> Result<CliOutput, String> {
    execution::execute(options)
}
