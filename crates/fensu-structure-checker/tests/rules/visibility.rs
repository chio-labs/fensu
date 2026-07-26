//! Visibility and entry-surface behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_visibility_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "an internal import from a bare crate export is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "use crate::Thing;\n\npub fn read_value(_: Thing) -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL103"],
        },
        test_types::CheckRepoTestCase {
            description: "an internal import from a concrete role module is accepted",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "use crate::models::Thing;\n\npub fn read_value(_: Thing) -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a cross-domain import of a private main entry is reported",
            repo_files: vec![
                helpers::main_module("reading", "pub(super) mod read_value;\n"),
                helpers::entry("reading", "read_value", "read_value"),
                helpers::entry_with_import(
                    "writing",
                    "write_value",
                    "use crate::reading::main::read_value::read_value;",
                ),
            ],
            expected_violation_codes: vec!["RSL104"],
        },
        test_types::CheckRepoTestCase {
            description: "a same-domain import of a private main entry is accepted",
            repo_files: vec![
                helpers::main_module("reading", "pub(super) mod read_value;\n"),
                helpers::entry("reading", "read_value", "read_value"),
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/calling.rs".to_owned(),
                    contents: "use crate::reading::main::read_value::read_value;\n\npub(crate) fn call() -> usize {\n    read_value()\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a public main entry without an external-domain importer is reported",
            repo_files: vec![
                helpers::main_module("reading", "pub(crate) mod read_value;\n"),
                helpers::entry("reading", "read_value", "read_value"),
            ],
            expected_violation_codes: vec!["RSL105"],
        },
        test_types::CheckRepoTestCase {
            description: "a same-domain importer does not earn public entry visibility",
            repo_files: vec![
                helpers::main_module("reading", "pub(crate) mod read_value;\n"),
                helpers::entry("reading", "read_value", "read_value"),
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/calling.rs".to_owned(),
                    contents: "use crate::reading::main::read_value::read_value;\n\npub(crate) fn call() -> usize {\n    read_value()\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSL105"],
        },
        test_types::CheckRepoTestCase {
            description: "an external-domain importer earns public entry visibility",
            repo_files: vec![
                helpers::main_module("reading", "pub(crate) mod read_value;\n"),
                helpers::entry("reading", "read_value", "read_value"),
                helpers::entry_with_import(
                    "writing",
                    "write_value",
                    "use crate::reading::main::read_value::read_value;",
                ),
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a test importer does not earn public entry visibility",
            repo_files: vec![
                helpers::main_module("reading", "pub(crate) mod read_value;\n"),
                helpers::entry("reading", "read_value", "read_value"),
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/test_importer.rs".to_owned(),
                    contents: "#![cfg(test)]\n\nuse crate::reading::main::read_value::read_value;\n\npub(crate) fn uses_entry() -> usize {\n    read_value()\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSL105"],
        },
        test_types::CheckRepoTestCase {
            description: "a cross-file reference to a private helper type is reported",
            repo_files: vec![
                helpers::entry("reading", "read_value", "read_value"),
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/rows.rs".to_owned(),
                    contents: "pub(super) struct Row;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/loading.rs".to_owned(),
                    contents: "use crate::reading::_helpers::rows::Row;\n\npub(crate) fn load() -> Row {\n    Row\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSL110"],
        },
        test_types::CheckRepoTestCase {
            description: "a crate-visible helper type may be shared within its domain",
            repo_files: vec![
                helpers::entry("reading", "read_value", "read_value"),
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/rows.rs".to_owned(),
                    contents: "pub(crate) struct Row;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/loading.rs".to_owned(),
                    contents: "use crate::reading::_helpers::rows::Row;\n\npub(crate) fn load() -> Row {\n    Row\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a helper re-export is reported",
            repo_files: vec![
                helpers::entry("reading", "read_value", "read_value"),
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/loading.rs".to_owned(),
                    contents: "pub(crate) use std::collections::HashMap;\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR404"],
        },
        test_types::CheckRepoTestCase {
            description: "a flat main entry colliding with a same-named bucket is reported",
            repo_files: vec![
                helpers::entry("reading", "read_value", "read_value"),
                test_types::RepoFile {
                    path: "crates/example/src/reading/main/read_value/format.rs".to_owned(),
                    contents: "pub fn format() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR302", "RSR405"],
        },
    ];

    for test_case in test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(&test_case);
        let actual_codes = helpers::collect_violation_codes(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert_eq!(
            actual_codes, test_case.expected_violation_codes,
            "case failed: {}",
            test_case.description
        );
    }
}
