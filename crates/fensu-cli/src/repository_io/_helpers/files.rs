//! Capability-confined, nofollow repository file access.

use std::io::{Read, Write};
use std::path::Path;

use cap_fs_ext::{FollowSymlinks, OpenOptionsFollowExt};
use cap_std::ambient_authority;
use cap_std::fs::{Dir, Metadata, OpenOptions};

use crate::repository_io::models::{FileIdentity, OperationLock, SafeFileSnapshot, WriteRequest};

pub(crate) fn open_repository(repository: &Path) -> Result<Dir, String> {
    Dir::open_ambient_dir(repository, ambient_authority())
        .map_err(|error| format!("Could not open repository safely: {error}"))
}

pub(crate) fn read_optional(
    repository: &Dir,
    path: &Path,
) -> Result<Option<SafeFileSnapshot>, String> {
    let mut options = OpenOptions::new();
    options.read(true).follow(FollowSymlinks::No);
    let mut file = match repository.open_with(path, &options) {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => {
            return Err(format!(
                "Refusing unsafe or unreadable repository file {}: {error}",
                path.display()
            ))
        }
    };
    let before = file.metadata().map_err(|error| error.to_string())?;
    if !before.is_file() {
        return Err(format!(
            "Refusing repository path because it is not a regular file: {}",
            path.display()
        ));
    }
    let mut content: Vec<u8> = Vec::new();
    file.read_to_end(&mut content)
        .map_err(|error| format!("Could not read {} safely: {error}", path.display()))?;
    let after = file.metadata().map_err(|error| error.to_string())?;
    let identity = file_identity(&before);
    if identity != file_identity(&after) || !after.is_file() {
        return Err(format!(
            "Repository file changed while it was being read: {}",
            path.display()
        ));
    }
    Ok(Some(SafeFileSnapshot {
        content,
        identity,
        permissions: after.permissions(),
    }))
}

pub(crate) fn write_if_unchanged(request: WriteRequest<'_>) -> Result<(), String> {
    let WriteRequest {
        repository,
        path,
        expected,
        content,
        temporary_prefix,
    } = request;
    let (temporary, mut file) = create_temporary(repository, temporary_prefix)?;
    let result = (|| {
        file.write_all(content)
            .map_err(|error| format!("Could not stage {}: {error}", path.display()))?;
        file.sync_all().map_err(|error| error.to_string())?;
        if let Some(snapshot) = expected {
            file.set_permissions(snapshot.permissions.clone())
                .map_err(|error| error.to_string())?;
        }
        let staged_identity = file_identity(&file.metadata().map_err(|error| error.to_string())?);
        let staged = read_optional(repository, Path::new(&temporary))?.ok_or_else(|| {
            "Repository staging file changed while update was being prepared.".to_owned()
        })?;
        if staged.identity != staged_identity || staged.content != content {
            return Err(
                "Repository staging file changed while update was being prepared; no changes made."
                    .to_owned(),
            );
        }
        let current = read_optional(repository, path)?;
        if !same_snapshot(current.as_ref(), expected) {
            return Err(format!(
                "Repository file changed while update was being prepared: {}; no changes made.",
                path.display()
            ));
        }
        if expected.is_none() {
            repository
                .hard_link(&temporary, repository, path)
                .map_err(|error| format!("Refusing to overwrite {}: {error}", path.display()))?;
            repository
                .remove_file(&temporary)
                .map_err(|error| error.to_string())?;
        } else {
            repository
                .rename(&temporary, repository, path)
                .map_err(|error| format!("Could not replace {} safely: {error}", path.display()))?;
        }
        let published = read_optional(repository, path)?
            .ok_or_else(|| format!("Published repository file disappeared: {}", path.display()))?;
        if published.content != content {
            return Err(format!(
                "Repository file changed during publication: {}",
                path.display()
            ));
        }
        Ok(())
    })();
    if result.is_err() {
        let _ = repository.remove_file(&temporary);
    }
    result
}

pub(crate) fn acquire_operation_lock(
    repository: &Dir,
    path: &str,
) -> Result<OperationLock, String> {
    let mut options = OpenOptions::new();
    options
        .write(true)
        .create_new(true)
        .follow(FollowSymlinks::No);
    let mut file = repository.open_with(path, &options).map_err(|error| {
        format!(
            "Could not acquire exclusive repository operation lock {path}: {error}. Another Fensu operation may be running; remove a stale regular lock only after confirming it is inactive."
        )
    })?;
    let content = format!(
        "pid={} thread={:?}\n",
        std::process::id(),
        std::thread::current().id()
    )
    .into_bytes();
    if let Err(error) = file.write_all(&content).and_then(|()| file.sync_all()) {
        drop(file);
        let _ = repository.remove_file(path);
        return Err(format!(
            "Could not initialize repository operation lock: {error}"
        ));
    }
    let metadata = file.metadata().map_err(|error| error.to_string())?;
    let identity = file_identity(&metadata);
    let repository = repository
        .try_clone()
        .map_err(|error| format!("Could not retain repository operation lock: {error}"))?;
    Ok(OperationLock {
        repository,
        path: path.to_owned(),
        identity,
        content,
    })
}

impl Drop for OperationLock {
    fn drop(&mut self) {
        let snapshot = match read_optional(&self.repository, Path::new(&self.path)) {
            Ok(Some(snapshot)) => snapshot,
            Ok(None) | Err(_) => return,
        };
        if snapshot.identity == self.identity && snapshot.content == self.content {
            let _ = self.repository.remove_file(&self.path);
        }
    }
}

fn create_temporary(repository: &Dir, prefix: &str) -> Result<(String, cap_std::fs::File), String> {
    for sequence in 0..1000 {
        let path = format!(
            ".{prefix}-{}-{:?}-{sequence}",
            std::process::id(),
            std::thread::current().id()
        );
        let mut options = OpenOptions::new();
        options
            .write(true)
            .create_new(true)
            .follow(FollowSymlinks::No);
        match repository.open_with(&path, &options) {
            Ok(file) => return Ok((path, file)),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(format!("Could not create safe staging file: {error}")),
        }
    }
    Err("Could not allocate a safe repository staging file.".to_owned())
}

fn same_snapshot(current: Option<&SafeFileSnapshot>, expected: Option<&SafeFileSnapshot>) -> bool {
    match (current, expected) {
        (None, None) => true,
        (Some(current), Some(expected)) => {
            current.identity == expected.identity && current.content == expected.content
        }
        (None, Some(_)) | (Some(_), None) => false,
    }
}

#[cfg(unix)]
fn file_identity(metadata: &Metadata) -> FileIdentity {
    use cap_std::fs::MetadataExt;

    FileIdentity {
        device: metadata.dev(),
        inode: metadata.ino(),
        changed_seconds: metadata.ctime(),
        changed_nanoseconds: metadata.ctime_nsec(),
        length: metadata.len(),
        modified: format!("{:?}", metadata.modified()),
    }
}

#[cfg(not(unix))]
fn file_identity(metadata: &Metadata) -> FileIdentity {
    FileIdentity {
        length: metadata.len(),
        modified: format!("{:?}", metadata.modified()),
    }
}
