//! Resource limits for isolated custom-rule host processes.

use std::time::Duration;

pub(crate) const RUST_HOST_TIMEOUT: Duration = Duration::from_secs(30);
pub(crate) const RUST_HOST_STDOUT_LIMIT: usize = 16 * 1024 * 1024;
pub(crate) const RUST_HOST_STDERR_LIMIT: usize = 1024 * 1024;
pub(crate) const WEB_HOST_TIMEOUT: Duration = Duration::from_secs(30);
pub(crate) const WEB_HOST_STDOUT_LIMIT: usize = 16 * 1024 * 1024;
pub(crate) const WEB_HOST_STDERR_LIMIT: usize = 1024 * 1024;
