//! Bulk DuckDB publication performance behavior.

use std::fs;
use std::time::{Duration, Instant};

use strata_memory::engine::main::rebuild_memory_index::rebuild_memory_index;

use crate::dependencies::helpers;
use crate::test_types::{MemoryPublicationPerformanceTestCase, MemoryPublicationStressTestCase};

#[test]
fn given_large_list_corpus_when_rebuilding_then_bulk_publication_stays_bounded() {
    let test_cases = [
        MemoryPublicationPerformanceTestCase {
            description:
                "publishes ten thousand distributed list items without row-at-a-time SQL overhead",
            document_count: 100,
            list_items_per_document: 100,
            list_marker: "",
            expected_list_item_count: 10_000,
            expected_list_item_batch_count: 1,
            expected_max_duration: Duration::from_secs(4),
        },
        MemoryPublicationPerformanceTestCase {
            description:
                "publishes ten thousand list items from one document without repeated source scans",
            document_count: 1,
            list_items_per_document: 10_000,
            list_marker: "",
            expected_list_item_count: 10_000,
            expected_list_item_batch_count: 1,
            expected_max_duration: Duration::from_secs(4),
        },
        MemoryPublicationPerformanceTestCase {
            description:
                "publishes ten thousand checkboxes through the same bounded list-item path",
            document_count: 1,
            list_items_per_document: 10_000,
            list_marker: "[ ] ",
            expected_list_item_count: 10_000,
            expected_list_item_batch_count: 1,
            expected_max_duration: Duration::from_secs(4),
        },
    ];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[]);
        let mut contents = String::from("# Bulk Publication\n\n");
        for index in 0..test_case.list_items_per_document {
            contents.push_str(&format!("- {}item {index}\n", test_case.list_marker));
        }
        let source_parent = root.join(".ai/knowledge/repo/notes");
        fs::create_dir_all(&source_parent).expect("source parent is writable");
        for index in 0..test_case.document_count {
            let source_name =
                format!("20260718T120000_{index:06}Z__NOTE-bulk-publication-{index}.md");
            fs::write(source_parent.join(source_name), &contents).expect("source is writable");
        }
        let database_path = root.join("memory.duckdb");
        let started = Instant::now();
        let summary = rebuild_memory_index(&root, &database_path).expect("rebuild succeeds");
        let elapsed = started.elapsed();

        assert_eq!(
            summary.list_item_count, test_case.expected_list_item_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            summary.list_item_batch_count, test_case.expected_list_item_batch_count,
            "{}",
            test_case.description
        );
        assert!(
            elapsed < test_case.expected_max_duration,
            "{}: {elapsed:?} exceeded {:?}",
            test_case.description,
            test_case.expected_max_duration
        );
        fs::remove_dir_all(root).expect("performance repository is removable");
    }
}

#[test]
#[ignore = "manual ten-million-row stress benchmark"]
fn given_ten_million_list_items_when_rebuilding_then_reports_stress_evidence() {
    let test_cases = [MemoryPublicationStressTestCase {
        description: "publishes ten thousand documents with one thousand list items each",
        document_count: 10_000,
        list_items_per_document: 1_000,
        expected_document_count: 10_000,
        expected_list_item_count: 10_000_000,
        expected_list_item_batch_count: 611,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[]);
        let source_parent = root.join(".ai/knowledge/repo/notes");
        fs::create_dir_all(&source_parent).expect("stress source parent is writable");
        let mut contents = String::from("# Stress Publication\n\n");
        for index in 0..test_case.list_items_per_document {
            contents.push_str(&format!("- item {index}\n"));
        }
        for index in 0..test_case.document_count {
            let source_name = format!("20260718T130000_{index:06}Z__NOTE-stress-{index}.md");
            fs::write(source_parent.join(source_name), &contents)
                .expect("stress source is writable");
        }
        let database_path = root.join("memory.duckdb");
        let started = Instant::now();
        let summary = rebuild_memory_index(&root, &database_path).expect("stress rebuild succeeds");
        let elapsed = started.elapsed();
        let database_bytes = fs::metadata(&database_path)
            .expect("stress database metadata is readable")
            .len();

        assert_eq!(
            summary.document_count, test_case.expected_document_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            summary.list_item_count, test_case.expected_list_item_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            summary.list_item_batch_count, test_case.expected_list_item_batch_count,
            "{}",
            test_case.description
        );
        eprintln!(
            "{}: elapsed={elapsed:?} database_bytes={database_bytes}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("stress repository is removable");
    }
}
