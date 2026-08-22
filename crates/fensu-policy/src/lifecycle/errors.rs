//! Structured lifecycle failures.

use std::fmt;

/// Product-neutral analysis lifecycle failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum LifecycleError {
    UnsupportedBatchSchema {
        actual: u32,
        expected: u32,
    },
    MissingCapabilities {
        capabilities: Vec<String>,
    },
    InvalidRepositoryPath {
        path: String,
    },
    InvalidPathPattern {
        pattern: String,
    },
    InvalidRuleCode {
        code: String,
    },
    InvalidConfiguration {
        message: String,
    },
    StaleSuppression {
        code: String,
        path: String,
        symbol: Option<String>,
        reason: String,
    },
    Serialization {
        message: String,
    },
    CacheIo {
        message: String,
    },
    HostLaunch {
        message: String,
    },
    HostFailure {
        message: String,
    },
    HostTimeout {
        timeout_millis: u64,
    },
    HostProtocol {
        actual: u32,
        expected: u32,
    },
    HostRuntimeVersion {
        actual: String,
        expected: String,
    },
    HostResponse {
        message: String,
    },
}

impl fmt::Display for LifecycleError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnsupportedBatchSchema { actual, expected } => write!(
                formatter,
                "unsupported analysis batch schema {actual}; expected {expected}"
            ),
            Self::MissingCapabilities { capabilities } => write!(
                formatter,
                "analysis runtime is missing required capabilities: {}",
                capabilities.join(", ")
            ),
            Self::InvalidRepositoryPath { path } => {
                write!(
                    formatter,
                    "path must be repository-relative POSIX text: {path}"
                )
            }
            Self::InvalidPathPattern { pattern } => {
                write!(formatter, "invalid repository path pattern: {pattern}")
            }
            Self::InvalidRuleCode { code } => {
                write!(
                    formatter,
                    "suppression requires one exact rule code: {code}"
                )
            }
            Self::InvalidConfiguration { message } => formatter.write_str(message),
            Self::StaleSuppression {
                code,
                path,
                symbol,
                reason,
            } => {
                let suffix = symbol
                    .as_ref()
                    .map_or_else(String::new, |value| format!("::{value}"));
                write!(
                    formatter,
                    "rule suppression no longer matches a finding: {code} {path}{suffix}. Remove it or update its scope. Reason: {reason}"
                )
            }
            Self::Serialization { message } => write!(formatter, "serialization failed: {message}"),
            Self::CacheIo { message } => write!(formatter, "cache operation failed: {message}"),
            Self::HostLaunch { message } => {
                write!(formatter, "could not launch custom host: {message}")
            }
            Self::HostFailure { message } => write!(formatter, "custom host failed: {message}"),
            Self::HostTimeout { timeout_millis } => write!(
                formatter,
                "custom host exceeded its {timeout_millis}ms execution timeout"
            ),
            Self::HostProtocol { actual, expected } => write!(
                formatter,
                "incompatible custom-host protocol {actual}; expected {expected}"
            ),
            Self::HostRuntimeVersion { actual, expected } => write!(
                formatter,
                "custom-host runtime version {actual} does not match {expected}"
            ),
            Self::HostResponse { message } => {
                write!(formatter, "invalid custom-host response: {message}")
            }
        }
    }
}

impl std::error::Error for LifecycleError {}
