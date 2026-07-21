//! Native cache test helpers.

use std::sync::Arc;
use std::thread;

use crate::cache::helpers::records::encode_canonical_record;
use crate::cache::helpers::storage::write_records;
use crate::cache::models::{CanonicalValue, EncodedWrite};

const MAXIMUM_RECORD_BYTES: usize = 1_000_000;

pub(crate) fn object(entries: &[(&str, CanonicalValue)]) -> CanonicalValue {
    CanonicalValue::Object(
        entries
            .iter()
            .map(|(key, value)| ((*key).to_owned(), value.clone()))
            .collect(),
    )
}

pub(crate) fn encoded_write(key: &str, kind: &str, payload: &CanonicalValue) -> EncodedWrite {
    EncodedWrite {
        key: key.to_owned(),
        kind: kind.to_owned(),
        data: encode_canonical_record(kind, payload, MAXIMUM_RECORD_BYTES)
            .expect("test record encodes"),
        insert_only: false,
    }
}

pub(crate) fn maximum_record_bytes() -> usize {
    MAXIMUM_RECORD_BYTES
}

pub(crate) fn concurrent_writes(repo_root: &std::path::Path, count: usize) -> Vec<bool> {
    let root = Arc::new(repo_root.to_path_buf());
    let handles = (0..count)
        .map(|value| {
            let root = Arc::clone(&root);
            thread::spawn(move || {
                let payload = object(&[("value", CanonicalValue::Integer(value.to_string()))]);
                write_records(
                    &root,
                    &[encoded_write("results/shared", "result", &payload)],
                )
                .is_some()
            })
        })
        .collect::<Vec<_>>();
    handles
        .into_iter()
        .map(|handle| handle.join().expect("writer thread joins"))
        .collect()
}
