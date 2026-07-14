//! Layer rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_layer_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "relative super import is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "use super::writing::write;\n\npub fn read_value() -> usize {\n    write()\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL001"],
        },
        test_types::CheckRepoTestCase {
            description: "wildcard import is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "use std::collections::*;\n\npub fn read_value() -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL002"],
        },
        test_types::CheckRepoTestCase {
            description: "crate absolute import is allowed",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "use crate::models::Thing;\n\npub fn read_value(thing: Thing) -> Thing {\n    thing\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "runtime crate depending on the checker is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/Cargo.toml".to_owned(),
                    contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nstrata-structure-checker.workspace = true\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSL301"],
        },
        test_types::CheckRepoTestCase {
            description: "malformed crate manifest fails closed",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSL901"],
        },
        test_types::CheckRepoTestCase {
            description: "crate without workspace lint inheritance is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL302"],
        },
        test_types::CheckRepoTestCase {
            description: "direct dependency policy is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nserde = \"*\"\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL304", "RSL307"],
        },
        test_types::CheckRepoTestCase {
            description: "workspace dependency policy is reported",
            repo_files: vec![test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.dependencies]\nserde = \"*\"\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL304"],
        },
        test_types::CheckRepoTestCase {
            description: "target dependency policy is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[target.'cfg(unix)'.dependencies]\nserde = \"*\"\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL304", "RSL307"],
        },
        test_types::CheckRepoTestCase {
            description: "renamed tooling dependency is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nchecker = { package = \"strata-structure-checker\", workspace = true }\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL301"],
        },
        test_types::CheckRepoTestCase {
            description: "malformed workspace manifest fails closed",
            repo_files: vec![test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSL901"],
        },
        test_types::CheckRepoTestCase {
            description: "missing required workspace lint is reported",
            repo_files: vec![test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL303"],
        },
        test_types::CheckRepoTestCase {
            description: "importing another domain's helpers is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/writing/main/write_value.rs".to_owned(),
                contents: "use crate::reading::helpers::loading::load;\n\npub fn write_value() -> usize {\n    load()\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSL101"],
        },
        test_types::CheckRepoTestCase {
            description: "importing own domain helpers is allowed",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "use crate::reading::helpers::loading::load;\n\npub fn read_value() -> usize {\n    load()\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
    ];

    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let actual_codes = helpers::collect_violation_codes(&repo_root);
        helpers::remove_temp_repo(&repo_root);

        assert_eq!(
            actual_codes, test_case.expected_violation_codes,
            "case failed: {}",
            test_case.description
        );
    }
}
