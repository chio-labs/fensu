//! Validate reviewed repository path collections and thresholds.

use crate::configuration::_helpers::repository_policy::{
    valid_repository_path, validate_non_empty_unique,
};
use crate::models;

pub(crate) fn validate_repository_policy(
    repository: &models::RepositoryPolicyConfig,
) -> Result<(), String> {
    validate_non_empty_unique(&repository.crate_names, "repository crate names")?;
    for (name, paths) in [
        ("domain paths", &repository.domain_paths),
        ("role paths", &repository.role_paths),
        (
            "intentional layout paths",
            &repository.intentional_layout_paths,
        ),
    ] {
        validate_non_empty_unique(paths, name)?;
        if let Some(path) = paths.iter().find(|path| !valid_repository_path(path)) {
            return Err(format!(
                "structure-checker {name} must be repository-relative POSIX paths: {path}"
            ));
        }
    }
    let thresholds = &repository.thresholds;
    if [
        thresholds.max_file_lines,
        thresholds.max_arguments,
        thresholds.max_statements_global,
        thresholds.max_statements_entry,
        thresholds.max_distinct_calls_entry,
        thresholds.max_locals_entry,
        thresholds.max_helper_container_modules,
        thresholds.max_main_container_modules,
    ]
    .contains(&0)
    {
        return Err("structure-checker thresholds must be greater than zero".to_owned());
    }
    Ok(())
}
