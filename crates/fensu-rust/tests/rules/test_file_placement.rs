//! Package layout and embedded resource ownership regression cases.

use crate::{helpers, test_types};

#[test]
fn given_package_entries_when_checking_then_reports_only_unowned_entries() {
    let test_cases = [
        test_types::CrateContentsTestCase {
            description: "package data directory",
            entries: &["data/value.txt"],
            options: "",
            expected_faults: 1,
        },
        test_types::CrateContentsTestCase {
            description: "stray file",
            entries: &["notes.txt"],
            options: "",
            expected_faults: 1,
        },
        test_types::CrateContentsTestCase {
            description: "file named target is not generated output",
            entries: &["target"],
            options: "",
            expected_faults: 1,
        },
        test_types::CrateContentsTestCase {
            description: "Cargo layout and generated paths",
            entries: &[
                "build.rs",
                "README.md",
                "LICENSE-MIT",
                "tests/data.txt",
                "benches/data.txt",
                "examples/data.txt",
                "target/data.txt",
                ".hidden/value.txt",
            ],
            options: "",
            expected_faults: 0,
        },
        test_types::CrateContentsTestCase {
            description: "configured allow list",
            entries: &["data/value.txt"],
            options: "[FPRSR311]\nallowed_entries = ['Cargo.toml', 'src/', 'data/']",
            expected_faults: 0,
        },
    ];
    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: test_case
                .entries
                .iter()
                .map(|entry| test_types::RepoFile {
                    path: format!("crates/example/{entry}"),
                    contents: String::new(),
                })
                .collect(),
            expected_violation_codes: Vec::new(),
        };
        let root = helpers::write_temp_repo_verbatim(&fixture);
        let options =
            toml::from_str::<toml::Table>(test_case.options).expect("valid fixture options");
        let policy =
            fensu_rust::configuration::main::rule_options::resolve_rule_options(Some(&options))
                .expect("valid policy");
        let violations =
            fensu_rust::rules::main::check_repository_with_config::check_repository_with_config(
                &root, &policy,
            )
            .expect("valid repository");
        helpers::remove_temp_repo(&root);
        assert_eq!(
            violations
                .iter()
                .filter(|violation| violation.code == "RSR311")
                .count(),
            test_case.expected_faults,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_embedded_files_when_checking_then_enforces_domain_boundaries() {
    let test_cases = [
        test_types::FilePlacementTestCase {
            description: "escape src",
            source: "const DATA: &str = include_str!(\"../../../x.txt\");",
            source_path: "src/orders/_helpers/data.rs",
            target: "x.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "cross domain",
            source: "const DATA: &str = include_str!(\"../../customers/data.txt\");",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "concat path",
            source: "const DATA: &str = include_str!(concat!(\"../\", \"data.txt\"));",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/orders/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "env path",
            source: "const DATA: &str = include_str!(env!(\"RESOURCE\"));",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/orders/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "qualified bytes",
            source: "static DATA: &[u8] = std::include_bytes!(\"../../customers/data.txt\");",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "missing target",
            source: "const DATA: &str = include_str!(\"missing.txt\");",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/orders/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "same domain",
            source: "const DATA: &str = include_str!(\"../data/file.txt\");",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/orders/data/file.txt",
            ownership_roots: &[],
            expected_faults: 0,
        },
        test_types::FilePlacementTestCase {
            description: "nested expression",
            source:
                "fn read() { println!(\"{}\", core::include_str!(\"../../customers/data.txt\")); }",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "repeat macro arguments",
            source: "fn read() { let data = vec![include_str!(\"../../customers/data.txt\"); 2]; }",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "nested nonliteral path",
            source: "fn read() { let data = vec![std::include_bytes!(concat!(\"../\", \"data.txt\")); 2]; }",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/orders/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "custom macro token grammar",
            source: "wrapper! { resource => { ::core::include_str!(\"../../customers/data.txt\") } ; }",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "custom namespace is not builtin include",
            source: "wrapper! { custom::include_str!(\"../../customers/data.txt\"); }",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 0,
        },
        test_types::FilePlacementTestCase {
            description: "each nested include is checked",
            source: "const DATA: &str = include_str!(include_str!(\"../../customers/data.txt\"));",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 2,
        },
        test_types::FilePlacementTestCase {
            description: "single literal with trailing comma",
            source: "static DATA: &[u8] = ::std::include_bytes!(\"../data.txt\",);",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/orders/data.txt",
            ownership_roots: &[],
            expected_faults: 0,
        },
        test_types::FilePlacementTestCase {
            description: "multiple literals",
            source: "const DATA: &str = include_str!(\"../data.txt\", \"../data.txt\");",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/orders/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "item macro",
            source: "include_str!(\"../../customers/data.txt\");",
            source_path: "src/orders/_helpers/data.rs",
            target: "src/customers/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "root file",
            source: "const DATA: &str = include_str!(\"orders/data.txt\");",
            source_path: "src/lib.rs",
            target: "src/orders/data.txt",
            ownership_roots: &[],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "configured ownership root",
            source: "const DATA: &str = include_str!(\"../../customers/data.txt\");",
            source_path: "src/group/orders/_helpers/data.rs",
            target: "src/group/customers/data.txt",
            ownership_roots: &["crates/example/src/group"],
            expected_faults: 1,
        },
        test_types::FilePlacementTestCase {
            description: "configured same domain",
            source: "const DATA: &str = include_str!(\"../data.txt\");",
            source_path: "src/group/orders/_helpers/data.rs",
            target: "src/group/orders/data.txt",
            ownership_roots: &["crates/example/src/group"],
            expected_faults: 0,
        },
    ];
    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: vec![
                test_types::RepoFile {
                    path: format!("crates/example/{}", test_case.source_path),
                    contents: test_case.source.to_owned(),
                },
                test_types::RepoFile {
                    path: format!("crates/example/{}", test_case.target),
                    contents: "resource".to_owned(),
                },
            ],
            expected_violation_codes: Vec::new(),
        };
        let root = helpers::write_temp_repo_verbatim(&fixture);
        let codes = helpers::collect_violation_codes_with_ownership_roots(
            &root,
            test_case
                .ownership_roots
                .iter()
                .map(|root| (*root).to_owned())
                .collect(),
        );
        helpers::remove_temp_repo(&root);
        assert_eq!(
            codes.iter().filter(|code| **code == "RSL106").count(),
            test_case.expected_faults,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_root_package_and_ignored_entries_when_checking_then_skips_member_containers() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "workspace members and ignore rules",
        repo_files: vec![
            test_types::RepoFile { path: "Cargo.toml".to_owned(), contents: "[package]\nname = 'root-package'\nversion = '0.1.0'\n[workspace]\nmembers = ['crates/example']\n[workspace.package]\nedition = '2021'\nlicense = 'MIT'\npublish = false\n[workspace.lints.rust]\nunsafe_code = 'forbid'\n".to_owned() },
            test_types::RepoFile { path: "src/lib.rs".to_owned(), contents: String::new() },
            test_types::RepoFile { path: ".gitignore".to_owned(), contents: "cache/\n*.tmp\n".to_owned() },
            test_types::RepoFile { path: "crates/example/cache/value.txt".to_owned(), contents: String::new() },
            test_types::RepoFile { path: "crates/example/file.tmp".to_owned(), contents: String::new() },
        ], expected_violation_codes: Vec::new(),
    }];
    for test_case in test_cases {
        let root = helpers::write_temp_repo_verbatim(&test_case);
        let codes = helpers::collect_violation_codes(&root);
        helpers::remove_temp_repo(&root);
        let placement_codes = codes
            .iter()
            .copied()
            .filter(|code| *code == "RSR311")
            .collect::<Vec<_>>();
        assert_eq!(
            placement_codes, test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
        assert!(!codes.contains(&"RSL901"), "{}", test_case.description);
    }
}

#[cfg(unix)]
#[test]
fn given_symlink_target_when_checking_then_resolves_physical_domain() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "symlink escapes domain",
        repo_files: vec![
            test_types::RepoFile {
                path: "crates/example/src/orders/constants.rs".to_owned(),
                contents: "const DATA: &str = include_str!(\"linked.txt\");".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/src/customers/data.txt".to_owned(),
                contents: "resource".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSL106"],
    }];
    for test_case in test_cases {
        let root = helpers::write_temp_repo_verbatim(&test_case);
        std::os::unix::fs::symlink(
            "../customers/data.txt",
            root.join("crates/example/src/orders/linked.txt"),
        )
        .expect("fixture symlink");
        let codes = helpers::collect_violation_codes(&root);
        helpers::remove_temp_repo(&root);
        let embedded_codes = codes
            .iter()
            .copied()
            .filter(|code| *code == "RSL106")
            .collect::<Vec<_>>();
        assert_eq!(
            embedded_codes, test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
    }
}
