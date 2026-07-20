use std::path::Path;

use crate::models::CliOutput;
use crate::skills::helpers::command::execution;
use crate::skills::models::SkillOptions;

pub(crate) fn execute(
    invocation: &Path,
    options: &SkillOptions,
    authoritative: bool,
) -> Result<CliOutput, String> {
    execution::execute(invocation, options, authoritative)
}
