//! Test-case types for native cache contracts.

use crate::cache::models::CanonicalValue;

pub(crate) struct CanonicalRecordTestCase {
    pub(crate) description: &'static str,
    pub(crate) kind: &'static str,
    pub(crate) payload: CanonicalValue,
    pub(crate) expected_bytes: &'static [u8],
}

pub(crate) struct InvalidRecordTestCase {
    pub(crate) description: &'static str,
    pub(crate) data: &'static [u8],
    pub(crate) expected_kind: &'static str,
    pub(crate) expected_present: bool,
}

pub(crate) struct CompressionTestCase {
    pub(crate) description: &'static str,
    pub(crate) payload_size: usize,
    pub(crate) expected_compressed: bool,
}

pub(crate) struct StorageRoundTripTestCase {
    pub(crate) description: &'static str,
    pub(crate) key: &'static str,
    pub(crate) kind: &'static str,
    pub(crate) expected_writes: usize,
    pub(crate) expected_reads: usize,
}

pub(crate) struct StorageRollbackTestCase {
    pub(crate) description: &'static str,
    pub(crate) failed_key: &'static str,
    pub(crate) expected_published: bool,
    pub(crate) expected_record: bool,
}

pub(crate) struct StorageMutationTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_retained: bool,
    pub(crate) expected_swept: bool,
    pub(crate) expected_written: bool,
    pub(crate) expected_unswept: bool,
}

pub(crate) struct StorageSafetyTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_published: bool,
    pub(crate) expected_external_database: bool,
}

pub(crate) struct ConcurrentStorageTestCase {
    pub(crate) description: &'static str,
    pub(crate) writer_count: usize,
    pub(crate) expected_success: bool,
}
