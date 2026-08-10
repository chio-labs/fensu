use std::fs;
use std::path::{Component, Path};

pub(crate) fn validate_target_path(repository: &Path, value: &str) -> Result<(), String> {
    let mut current = repository.to_path_buf();
    for component in Path::new(value).components() {
        if component == Component::CurDir {
            continue;
        }
        let Component::Normal(part) = component else {
            return Err("Target path must remain inside the repository.".to_owned());
        };
        current.push(part);
        let metadata = fs::symlink_metadata(&current).map_err(|error| {
            format!("Target path {value} is not an existing safe directory: {error}")
        })?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(format!(
                "Target path {value} must not contain symlinks and must remain inside the repository."
            ));
        }
    }
    validate_source_root(repository, value)
}

fn validate_source_root(repository: &Path, value: &str) -> Result<(), String> {
    let path = repository.join(value).join("src");
    let metadata = match fs::symlink_metadata(&path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Err(format!(
                "SvelteKit target path {value} must contain a src directory."
            ))
        }
        Err(error) => return Err(error.to_string()),
    };
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(format!(
            "SvelteKit target path {value} must contain a non-symlink src directory."
        ));
    }
    Ok(())
}
