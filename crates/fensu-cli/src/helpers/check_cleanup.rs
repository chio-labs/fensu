use std::collections::BTreeSet;
use std::ffi::{OsStr, OsString};
use std::path::{Component, Path, PathBuf};

use cap_fs_ext::DirExt;
use cap_std::ambient_authority;
use cap_std::fs::{Dir, DirEntry};

use crate::configuration::main::load;
use crate::constants::PYTHON_CACHE_DIRECTORY;
use crate::models::Config;

pub(crate) struct CleanupPlan {
    repository: Dir,
    config: Config,
}

impl CleanupPlan {
    pub(crate) fn run(&self) {
        cleanup_configured_roots(&self.repository, &self.config);
    }
}

pub(crate) fn prepare(invocation: &Path) -> Option<CleanupPlan> {
    let invocation_directory = Dir::open_ambient_dir(invocation, ambient_authority()).ok()?;
    let invocation_path = invocation.canonicalize().ok()?;
    let Ok((config_path, config)) = load::load(invocation) else {
        return None;
    };
    let repository_path = config_path.parent()?;
    let relative = invocation_path.strip_prefix(repository_path).ok()?;
    let mut repository = invocation_directory;
    for _ in relative.components() {
        repository = repository.open_parent_dir(ambient_authority()).ok()?;
    }
    let config_name = config_path.file_name()?;
    (repository.read(config_name).ok()? == config.raw).then_some(CleanupPlan { repository, config })
}

fn cleanup_configured_roots(repository: &Dir, config: &Config) {
    let protected_roots = configured_roots(config);
    for configured_root in &protected_roots {
        let Some(directory) = open_directory(repository, configured_root) else {
            continue;
        };
        clean_directory(&directory, configured_root, &protected_roots);
    }
}

fn configured_roots(config: &Config) -> BTreeSet<PathBuf> {
    config
        .roots
        .iter()
        .chain(&config.tests)
        .chain(&config.tooling)
        .filter_map(|path| resolve_configured_root(path))
        .collect()
}

fn resolve_configured_root(configured: &str) -> Option<PathBuf> {
    let mut resolved = PathBuf::new();
    for component in Path::new(configured).components() {
        match component {
            Component::Normal(part) => resolved.push(part),
            Component::CurDir => {}
            Component::ParentDir if !resolved.as_os_str().is_empty() => {
                let _ = resolved.pop();
            }
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => return None,
        }
    }
    (!resolved.as_os_str().is_empty()).then_some(resolved)
}

fn open_directory(repository: &Dir, path: &Path) -> Option<Dir> {
    let mut directory = repository.try_clone().ok()?;
    for component in path.components() {
        let Component::Normal(name) = component else {
            return None;
        };
        directory = directory.open_dir_nofollow(name).ok()?;
    }
    Some(directory)
}

fn clean_directory(directory: &Dir, relative: &Path, protected_roots: &BTreeSet<PathBuf>) {
    let Ok(entries) = sorted_entries(directory) else {
        return;
    };
    for entry in entries {
        let name = entry.file_name();
        let path = relative.join(&name);
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        if !file_type.is_dir()
            || file_type.is_symlink()
            || is_cache_directory(&name)
            || protected_roots.contains(&path)
        {
            continue;
        }
        let Ok(child) = directory.open_dir_nofollow(&name) else {
            continue;
        };
        clean_directory(&child, &path, protected_roots);
        let _ = directory.remove_dir(&name);
    }

    let Ok(entries) = sorted_entries(directory) else {
        return;
    };
    if entries.is_empty() {
        return;
    }

    let mut cache_directories = Vec::new();
    let mut blocked = false;
    for entry in entries {
        let name = entry.file_name();
        let Ok(file_type) = entry.file_type() else {
            blocked = true;
            continue;
        };
        if file_type.is_symlink() {
            blocked = true;
        } else if file_type.is_dir() && is_cache_directory(&name) {
            let Ok(cache_directory) = directory.open_dir_nofollow(&name) else {
                blocked = true;
                continue;
            };
            if cache_tree_is_disposable(&cache_directory) {
                cache_directories.push((name, cache_directory));
            } else {
                blocked = true;
            }
        } else {
            blocked = true;
        }
    }

    if blocked {
        for (_, cache_directory) in cache_directories {
            remove_empty_directories(&cache_directory);
        }
        return;
    }

    for (name, cache_directory) in cache_directories {
        remove_disposable_cache_tree(&cache_directory);
        let _ = directory.remove_dir(name);
    }
}

fn cache_tree_is_disposable(directory: &Dir) -> bool {
    let Ok(entries) = sorted_entries(directory) else {
        return false;
    };
    entries.into_iter().all(|entry| {
        let name = entry.file_name();
        let Ok(file_type) = entry.file_type() else {
            return false;
        };
        if file_type.is_symlink() {
            false
        } else if file_type.is_dir() {
            directory
                .open_dir_nofollow(&name)
                .is_ok_and(|child| cache_tree_is_disposable(&child))
        } else {
            file_type.is_file() && is_bytecode(&name)
        }
    })
}

fn remove_disposable_cache_tree(directory: &Dir) {
    if !cache_tree_is_disposable(directory) {
        return;
    }
    let Ok(entries) = sorted_entries(directory) else {
        return;
    };
    for entry in entries {
        let name = entry.file_name();
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        if file_type.is_dir() && !file_type.is_symlink() {
            let Ok(child) = directory.open_dir_nofollow(&name) else {
                continue;
            };
            remove_disposable_cache_tree(&child);
            let _ = directory.remove_dir(&name);
        } else if file_type.is_file() && is_bytecode(&name) {
            let _ = directory.remove_file(&name);
        }
    }
}

fn remove_empty_directories(directory: &Dir) {
    let Ok(entries) = sorted_entries(directory) else {
        return;
    };
    for entry in entries {
        let name = entry.file_name();
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        if file_type.is_dir() && !file_type.is_symlink() {
            let Ok(child) = directory.open_dir_nofollow(&name) else {
                continue;
            };
            remove_empty_directories(&child);
            let _ = directory.remove_dir(&name);
        }
    }
}

fn sorted_entries(directory: &Dir) -> Result<Vec<DirEntry>, std::io::Error> {
    let mut entries = directory.entries()?.collect::<Result<Vec<_>, _>>()?;
    entries.sort_by_key(DirEntry::file_name);
    Ok(entries)
}

fn is_cache_directory(name: &OsStr) -> bool {
    name == PYTHON_CACHE_DIRECTORY
}

fn is_bytecode(name: &OsString) -> bool {
    matches!(
        Path::new(name)
            .extension()
            .and_then(|extension| extension.to_str()),
        Some("pyc" | "pyo")
    )
}
