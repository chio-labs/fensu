use std::path::Path;

use crate::models::{Config, RuleMetadata};
use crate::skills::helpers::context::selection;

pub(crate) fn load_rule_catalogue(
    config: &Config,
    project_root: &Path,
) -> Result<Vec<RuleMetadata>, String> {
    Ok(selection::selection(config, project_root)?.catalogue)
}
