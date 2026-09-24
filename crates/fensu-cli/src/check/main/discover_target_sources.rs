//! Discover the analysable sources of one target with the check command's selection rules.

use std::path::Path;

use crate::check::_helpers::preparation::{discover, select_sources};
use crate::models::{Config, ScopedSource, SourcePurpose};

/// Return configured root, test, and tooling sources after generated-path and evaluation filters.
pub(crate) fn discover_target_sources(
    root: &Path,
    project_root: &Path,
    config: &Config,
) -> Result<Vec<ScopedSource>, String> {
    let (sources, _) = select_sources(discover(root, project_root, config)?, config);
    Ok(sources
        .into_iter()
        .filter(|source| {
            matches!(
                source.purpose,
                SourcePurpose::Direct | SourcePurpose::Support
            )
        })
        .collect())
}
