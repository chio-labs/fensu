//! Structured failures returned by memory engine operations.

use std::error::Error;
use std::fmt;
use std::io;
use std::path::PathBuf;

/// A structured failure from memory publication or read-only querying.
#[derive(Debug)]
pub enum MemoryIndexError {
    InvalidDatabasePath(PathBuf),
    DatabaseNotFound(PathBuf),
    EmptyQuery,
    QueryTooLong {
        actual_bytes: usize,
        maximum_bytes: usize,
    },
    InvalidQueryLimit {
        limit: usize,
        minimum: usize,
        maximum: usize,
    },
    TooManyQueryColumns {
        actual: usize,
        maximum: usize,
    },
    QueryResultTooLarge {
        approximate_bytes: usize,
        maximum_bytes: usize,
    },
    QueryValueTooDeep {
        depth: usize,
        maximum_depth: usize,
    },
    QueryMetadataUnavailable,
    MissingResolvedLink {
        document_identity: String,
        link_ordinal: usize,
    },
    Archive(String),
    Filesystem {
        operation: &'static str,
        path: PathBuf,
        source: io::Error,
    },
    DuckDb {
        operation: &'static str,
        source: duckdb::Error,
    },
    Cleanup {
        path: PathBuf,
        source: io::Error,
        original: Box<MemoryIndexError>,
    },
}

impl MemoryIndexError {
    pub(crate) fn filesystem(operation: &'static str, path: PathBuf, source: io::Error) -> Self {
        Self::Filesystem {
            operation,
            path,
            source,
        }
    }

    pub(crate) fn duckdb(operation: &'static str, source: duckdb::Error) -> Self {
        Self::DuckDb { operation, source }
    }
}

impl fmt::Display for MemoryIndexError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidDatabasePath(path) => {
                write!(
                    formatter,
                    "database path has no file name: {}",
                    path.display()
                )
            }
            Self::DatabaseNotFound(path) => write!(
                formatter,
                "memory index database does not exist: {}",
                path.display()
            ),
            Self::EmptyQuery => write!(formatter, "memory query is empty"),
            Self::QueryTooLong {
                actual_bytes,
                maximum_bytes,
            } => write!(
                formatter,
                "memory query is {actual_bytes} bytes; maximum is {maximum_bytes} bytes"
            ),
            Self::InvalidQueryLimit {
                limit,
                minimum,
                maximum,
            } => write!(
                formatter,
                "memory query limit {limit} is invalid; expected {minimum}..={maximum}"
            ),
            Self::TooManyQueryColumns { actual, maximum } => write!(
                formatter,
                "memory query returned {actual} columns; maximum is {maximum}"
            ),
            Self::QueryResultTooLarge {
                approximate_bytes,
                maximum_bytes,
            } => write!(
                formatter,
                "memory query result is approximately {approximate_bytes} bytes; maximum is {maximum_bytes} bytes"
            ),
            Self::QueryValueTooDeep {
                depth,
                maximum_depth,
            } => write!(
                formatter,
                "memory query value depth {depth} exceeds maximum depth {maximum_depth}"
            ),
            Self::QueryMetadataUnavailable => {
                write!(formatter, "DuckDB did not expose memory query result metadata")
            }
            Self::MissingResolvedLink {
                document_identity,
                link_ordinal,
            } => write!(
                formatter,
                "resolved graph has no link {link_ordinal} for document {document_identity}"
            ),
            Self::Archive(message) => write!(formatter, "memory archive failed: {message}"),
            Self::Filesystem {
                operation,
                path,
                source,
            } => write!(formatter, "{operation} {}: {source}", path.display()),
            Self::DuckDb { operation, source } => write!(formatter, "{operation}: {source}"),
            Self::Cleanup {
                path,
                source,
                original,
            } => write!(
                formatter,
                "{original}; also failed to remove temporary file {}: {source}",
                path.display()
            ),
        }
    }
}

impl Error for MemoryIndexError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::InvalidDatabasePath(_)
            | Self::DatabaseNotFound(_)
            | Self::EmptyQuery
            | Self::QueryTooLong { .. }
            | Self::InvalidQueryLimit { .. }
            | Self::TooManyQueryColumns { .. }
            | Self::QueryResultTooLarge { .. }
            | Self::QueryValueTooDeep { .. }
            | Self::QueryMetadataUnavailable
            | Self::MissingResolvedLink { .. }
            | Self::Archive(_) => None,
            Self::Filesystem { source, .. } | Self::Cleanup { source, .. } => Some(source),
            Self::DuckDb { source, .. } => Some(source),
        }
    }
}
