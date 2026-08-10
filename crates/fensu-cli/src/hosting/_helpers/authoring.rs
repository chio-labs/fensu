//! Resolve and verify the installed authoring package version.

use std::env;
use std::path::{Path, PathBuf};

pub(crate) fn verify_authoring_version() -> Result<(), String> {
    let Some(version) = installed_authoring_version() else {
        return Err(
            "fensu is not installed beside fensu-cli; install `fensu` or use the CLI package only for `--version`."
                .to_owned(),
        );
    };
    if version != env!("CARGO_PKG_VERSION") {
        return Err(format!(
            "fensu-cli {} does not match installed fensu {version}. Upgrade both packages together with `python -m pip install --upgrade fensu`. ",
            env!("CARGO_PKG_VERSION")
        ));
    }
    Ok(())
}

fn installed_authoring_version() -> Option<String> {
    let mut prefixes: Vec<PathBuf> = Vec::new();
    if let Ok(executable) = env::current_exe() {
        if let Some(prefix) = executable.parent().and_then(Path::parent) {
            prefixes.push(prefix.to_path_buf());
        }
    }
    if let Some(executable) = env::var_os("FENSU_PYTHON") {
        if let Some(prefix) = Path::new(&executable).parent().and_then(Path::parent) {
            if !prefixes.iter().any(|candidate| candidate == prefix) {
                prefixes.push(prefix.to_path_buf());
            }
        }
    }
    for prefix in prefixes {
        let candidates = [prefix.join("Lib/site-packages"), prefix.join("lib")];
        for candidate in candidates {
            if candidate.ends_with("lib") {
                let Ok(entries) = candidate.read_dir() else {
                    continue;
                };
                for entry in entries.flatten() {
                    let site = entry.path().join("site-packages");
                    if let Some(version) = metadata_version(&site) {
                        return Some(version);
                    }
                }
            } else if let Some(version) = metadata_version(&candidate) {
                return Some(version);
            }
        }
    }
    None
}

fn metadata_version(site_packages: &Path) -> Option<String> {
    let Ok(entries) = site_packages.read_dir() else {
        return None;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let name = path.file_name()?.to_str()?;
        if !name.starts_with("fensu-") || !name.ends_with(".dist-info") {
            continue;
        }
        let Ok(metadata) = std::fs::read_to_string(path.join("METADATA")) else {
            return None;
        };
        return metadata
            .lines()
            .find_map(|line| line.strip_prefix("Version: ").map(str::to_owned));
    }
    None
}
