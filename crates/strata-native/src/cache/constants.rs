//! Persistent cache schema constants shared by native cache operations.

pub(crate) const APPLICATION_ID: i32 = 0x5354_5241;
pub(crate) const BUSY_TIMEOUT_MS: u64 = 1_000;
pub(crate) const CACHE_RELATIVE_PATH: &str = ".strata/cache/v4.db";
pub(crate) const COMPRESSED_PREFIX: &[u8] = b"strata-zlib-v1\0";
pub(crate) const COMPRESSION_LEVEL: u32 = 1;
pub(crate) const COMPRESSION_THRESHOLD: usize = 512;
pub(crate) const ENVELOPE_KEY_COUNT: usize = 3;
pub(crate) const MAXIMUM_BASIC_MULTILINGUAL_PLANE: u32 = 0xffff;
pub(crate) const PYTHON_GLOB_PATTERN: &str = "*.py";
pub(crate) const RECORD_SCHEMA_VERSION: i64 = 4;
pub(crate) const STORAGE_SCHEMA_VERSION: i32 = 1;
pub(crate) const READ_CHUNK_SIZE: usize = 500;
