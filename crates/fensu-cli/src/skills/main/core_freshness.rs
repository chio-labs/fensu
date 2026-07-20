use std::path::Path;

use crate::skills::helpers::command::execution;

pub(crate) fn core_freshness(invocation: &Path) -> Result<String, String> {
    execution::core_freshness(invocation)
}
