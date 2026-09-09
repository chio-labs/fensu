//! Resolve configured values in owned native catalogue metadata.

use crate::catalogue::_helpers::policy::apply_native_option_values;
use crate::catalogue::models::RuleMetadata;
use crate::models::Config;

pub(crate) fn resolve_native_options(
    mut catalogue: Vec<RuleMetadata>,
    config: &Config,
) -> Result<Vec<RuleMetadata>, String> {
    apply_native_option_values(&mut catalogue, config)?;
    Ok(catalogue)
}
