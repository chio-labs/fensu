//! Transactional native cache-storage contracts.

use rusqlite::Connection;

use crate::cache::helpers::database::database_path;
use crate::cache::helpers::storage::{mutate_records, read_records, write_records};
use crate::cache::models::{CacheMutation, CanonicalValue};
use crate::cache::tests::helpers::{
    concurrent_writes, encoded_write, maximum_record_bytes, object,
};
use crate::cache::tests::test_types::{
    ConcurrentStorageTestCase, StorageMutationTestCase, StorageRollbackTestCase,
    StorageRoundTripTestCase, StorageSafetyTestCase,
};

#[test]
fn given_encoded_record_when_writing_then_transaction_round_trips() {
    let test_cases = [StorageRoundTripTestCase {
        description: "one native write is visible to an independent read",
        key: "results/result.json",
        kind: "result",
        expected_writes: 1,
        expected_reads: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect(test_case.description);
        let payload = object(&[(
            "path",
            CanonicalValue::String("src/pkg/module.py".to_owned()),
        )]);
        let write = encoded_write(test_case.key, test_case.kind, &payload);
        let written = write_records(repository.path(), &[write]).expect(test_case.description);
        let (records, read) = read_records(
            repository.path(),
            &[(test_case.key.to_owned(), test_case.kind.to_owned())],
            maximum_record_bytes(),
        )
        .expect(test_case.description);

        assert_eq!(
            written.writes, test_case.expected_writes,
            "{}",
            test_case.description
        );
        assert_eq!(
            read.reads, test_case.expected_reads,
            "{}",
            test_case.description
        );
        assert_eq!(
            records[0].as_ref().map(|record| &record.payload),
            Some(&payload),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_later_write_failure_when_publishing_then_transaction_rolls_back() {
    let test_cases = [StorageRollbackTestCase {
        description: "triggered second-row failure publishes no earlier row",
        failed_key: "results/second",
        expected_published: false,
        expected_record: false,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect(test_case.description);
        let setup = object(&[]);
        write_records(
            repository.path(),
            &[encoded_write("setup", "setup", &setup)],
        )
        .expect(test_case.description);
        let connection = Connection::open(database_path(repository.path()))
            .expect("cache database opens for failure trigger");
        connection
            .execute_batch(&format!(
                "CREATE TRIGGER fail_writes BEFORE INSERT ON records WHEN NEW.key = '{}' BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END",
                test_case.failed_key
            ))
            .expect("failure trigger installs");
        let payload = object(&[("value", CanonicalValue::Integer("1".to_owned()))]);
        let outcome = write_records(
            repository.path(),
            &[
                encoded_write("results/first", "result", &payload),
                encoded_write(test_case.failed_key, "result", &payload),
            ],
        );
        let (records, _) = read_records(
            repository.path(),
            &[("results/first".to_owned(), "result".to_owned())],
            maximum_record_bytes(),
        )
        .expect(test_case.description);

        assert_eq!(
            outcome.is_some(),
            test_case.expected_published,
            "{}",
            test_case.description
        );
        assert_eq!(
            records[0].is_some(),
            test_case.expected_record,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_seeded_records_when_mutating_then_writes_retains_and_sweeps_atomically() {
    let test_cases = [StorageMutationTestCase {
        description: "mutation preserves retained and unrelated rows while replacing generation",
        expected_retained: true,
        expected_swept: false,
        expected_written: true,
        expected_unswept: true,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect(test_case.description);
        let file_payload = object(&[("path", CanonicalValue::String("src/a.py".to_owned()))]);
        let metadata = object(&[]);
        write_records(
            repository.path(),
            &[
                encoded_write("results/aa/keep", "file_result", &file_payload),
                encoded_write("results/aa/old", "file_result", &file_payload),
                encoded_write("metadata", "metadata", &metadata),
            ],
        )
        .expect(test_case.description);
        let written_payload = object(&[("path", CanonicalValue::String("src/b.py".to_owned()))]);
        mutate_records(
            repository.path(),
            &[("metadata".to_owned(), "metadata".to_owned())],
            maximum_record_bytes(),
            |_| {
                Ok(Some(CacheMutation {
                    writes: vec![encoded_write(
                        "results/bb/new",
                        "file_result",
                        &written_payload,
                    )],
                    swept_prefix: Some("results".to_owned()),
                    retained_paths: vec!["results/aa/keep".to_owned()],
                    deleted_paths: Vec::new(),
                }))
            },
        )
        .expect(test_case.description);
        let (records, _) = read_records(
            repository.path(),
            &[
                ("results/aa/keep".to_owned(), "file_result".to_owned()),
                ("results/aa/old".to_owned(), "file_result".to_owned()),
                ("results/bb/new".to_owned(), "file_result".to_owned()),
                ("metadata".to_owned(), "metadata".to_owned()),
            ],
            maximum_record_bytes(),
        )
        .expect(test_case.description);

        assert_eq!(
            records[0].is_some(),
            test_case.expected_retained,
            "{}",
            test_case.description
        );
        assert_eq!(
            records[1].is_some(),
            test_case.expected_swept,
            "{}",
            test_case.description
        );
        assert_eq!(
            records[2].is_some(),
            test_case.expected_written,
            "{}",
            test_case.description
        );
        assert_eq!(
            records[3].is_some(),
            test_case.expected_unswept,
            "{}",
            test_case.description
        );
    }
}

#[cfg(unix)]
#[test]
fn given_symlinked_cache_parent_when_writing_then_refuses_external_storage() {
    let test_cases = [StorageSafetyTestCase {
        description: "symlinked .fensu directory cannot escape the repository",
        expected_published: false,
        expected_external_database: false,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect(test_case.description);
        let external = tempfile::tempdir().expect("external directory is creatable");
        std::os::unix::fs::symlink(external.path(), repository.path().join(".fensu"))
            .expect("cache parent symlink is creatable");
        let payload = object(&[]);
        let outcome = write_records(
            repository.path(),
            &[encoded_write("metadata", "metadata", &payload)],
        );

        assert_eq!(
            outcome.is_some(),
            test_case.expected_published,
            "{}",
            test_case.description
        );
        assert_eq!(
            database_path(external.path()).exists(),
            test_case.expected_external_database,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_concurrent_writers_when_publishing_then_one_complete_record_remains() {
    let test_cases = [ConcurrentStorageTestCase {
        description: "racing writers publish at least one complete record",
        writer_count: 8,
        expected_success: true,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect(test_case.description);
        let outcomes = concurrent_writes(repository.path(), test_case.writer_count);
        let (records, _) = read_records(
            repository.path(),
            &[("results/shared".to_owned(), "result".to_owned())],
            maximum_record_bytes(),
        )
        .expect(test_case.description);

        assert_eq!(
            outcomes.iter().any(|outcome| *outcome),
            test_case.expected_success,
            "{}",
            test_case.description
        );
        assert_eq!(
            records[0].is_some(),
            test_case.expected_success,
            "{}",
            test_case.description
        );
    }
}
