use std::path::Path;

use crate::models::Config;
use crate::skills::_helpers::context::selection;
use crate::skills::models::RuleSelection;

pub(crate) fn load_rule_selection(
    config: &Config,
    project_root: &Path,
) -> Result<RuleSelection, String> {
    selection::selection(config, project_root)
}
