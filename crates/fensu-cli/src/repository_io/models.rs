use std::path::Path;

use cap_std::fs::{Dir, Permissions};

#[derive(Debug)]
pub(crate) struct SafeFileSnapshot {
    pub(crate) content: Vec<u8>,
    pub(crate) identity: FileIdentity,
    pub(crate) permissions: Permissions,
}

#[derive(Debug)]
pub(crate) struct WriteRequest<'a> {
    pub(crate) repository: &'a Dir,
    pub(crate) path: &'a Path,
    pub(crate) expected: Option<&'a SafeFileSnapshot>,
    pub(crate) content: &'a [u8],
    pub(crate) temporary_prefix: &'a str,
}

#[derive(Debug)]
pub(crate) struct OperationLock {
    pub(crate) repository: Dir,
    pub(crate) path: String,
    pub(crate) identity: FileIdentity,
    pub(crate) content: Vec<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FileIdentity {
    #[cfg(unix)]
    pub(crate) device: u64,
    #[cfg(unix)]
    pub(crate) inode: u64,
    #[cfg(unix)]
    pub(crate) changed_seconds: i64,
    #[cfg(unix)]
    pub(crate) changed_nanoseconds: i64,
    pub(crate) length: u64,
    pub(crate) modified: String,
}
