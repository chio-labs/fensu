//! Consumer configuration behavior over fixture repositories.

use crate::helpers;
use crate::test_types;
use fensu_rust::models;
use fensu_rust::rules::main::check_repository_with_config;

#[test]
fn given_default_policy_when_checking_then_parser_identities_are_repository_neutral() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "default raw parser boundary",
        repo_files: vec![
            test_types::RepoFile {
                path: "crates/example/src/rules/_helpers/annotations.rs".to_owned(),
                contents: "use ruff_python_ast::ModModule;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/src/facts/_helpers/annotations.rs".to_owned(),
                contents: "use ruff_python_ast::ModModule;\ntype Parsed = ruff_python_ast::Expr;\n"
                    .to_owned(),
            },
        ],
        expected_violation_codes: Vec::new(),
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        let parser_violations = violations
            .iter()
            .filter(|violation| violation.code == "RSL102")
            .map(|violation| violation.code)
            .collect::<Vec<_>>();
        assert_eq!(
            parser_violations, test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_nonempty_structural_inventories_when_checking_then_undeclared_paths_fail_closed() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "closed domain and role inventories",
        repo_files: vec![
            helpers::entry("reading", "read_value", "read_value"),
            helpers::entry("writing", "write_value", "write_value"),
        ],
        expected_violation_codes: vec!["RSL305", "RSL305"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let mut config = models::RustPolicy::default();
        config.repository.domain_paths = vec!["crates/example/src/reading".to_owned()];
        config.repository.role_paths = vec!["crates/example/src/reading/main".to_owned()];
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("closed inventories are valid configuration");
        helpers::remove_temp_repo(&repo_root);
        let undeclared = violations
            .iter()
            .filter(|violation| violation.code == test_case.expected_violation_codes[0])
            .map(|violation| violation.path.to_string_lossy().into_owned())
            .collect::<Vec<_>>();
        assert_eq!(
            vec!["RSL305"; undeclared.len()],
            test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
        assert_eq!(
            undeclared,
            vec![
                "crates/example/src/writing".to_owned(),
                "crates/example/src/writing/main".to_owned(),
            ],
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_custom_parser_scope_when_checking_then_all_rust_reference_forms_are_blocked() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "raw parser syntax coverage",
        repo_files: vec![
            test_types::RepoFile {
                path: "crates/example/src/policy/main/check.rs".to_owned(),
                contents: "use parser_use::Thing;\nextern crate parser_extern;\ntype Parsed = parser_path::Thing;\nfn check() { parser_macro::parse!(); }\nmacro_rules! wrap { () => { type Hidden = parser_token::Thing; } }\nmacro_rules! harmless { ($parser_token:ident) => { let parser_token = 1; } }\n#[some_macro(parser = parser_attr::Expr)] fn attributed() {}\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/src/outside/main/check.rs".to_owned(),
                contents: "use parser_use::Thing;\n".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSL102", "RSL102", "RSL102", "RSL102", "RSL102", "RSL102"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let mut config = models::RustPolicy::default();
        config.raw_parser_boundary.packages = vec![
            "parser_use".to_owned(),
            "parser_extern".to_owned(),
            "parser_path".to_owned(),
            "parser_macro".to_owned(),
            "parser_token".to_owned(),
            "parser_attr".to_owned(),
        ];
        config.raw_parser_boundary.restricted_paths = vec!["crates/example/src/policy".to_owned()];
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("custom parser scope is valid");
        helpers::remove_temp_repo(&repo_root);
        let parser = violations
            .iter()
            .filter(|violation| violation.code == test_case.expected_violation_codes[0])
            .map(|violation| (violation.line, violation.message.clone()))
            .collect::<Vec<_>>();
        assert_eq!(
            vec!["RSL102"; parser.len()],
            test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
        assert_eq!(
            parser,
            vec![
                (
                    Some(1),
                    "restricted module accesses raw parser crate parser_use".to_owned()
                ),
                (
                    Some(2),
                    "restricted module accesses raw parser crate parser_extern".to_owned()
                ),
                (
                    Some(3),
                    "restricted module accesses raw parser crate parser_path".to_owned()
                ),
                (
                    Some(4),
                    "restricted module accesses raw parser crate parser_macro".to_owned()
                ),
                (
                    Some(5),
                    "restricted module accesses raw parser crate parser_token".to_owned()
                ),
                (
                    Some(7),
                    "restricted module accesses raw parser crate parser_attr".to_owned()
                ),
            ],
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_renamed_parser_dependency_when_checking_then_source_alias_is_blocked() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "Cargo dependency alias resolves to parser package identity",
        repo_files: vec![
            test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace]\nmembers = [\"crates/example\", \"crates/raw-parser\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nast = { package = \"raw-parser\", path = \"crates/raw-parser\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nast.workspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/src/rules/main/check.rs".to_owned(),
                contents: "use ast::Expr;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/raw-parser/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"raw-parser\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/raw-parser/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub struct Expr;\n".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSL102"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let mut config = models::RustPolicy::default();
        config.raw_parser_boundary.packages = vec!["raw-parser".to_owned()];
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("renamed parser dependency is valid Cargo metadata");
        helpers::remove_temp_repo(&repo_root);
        let parser = violations
            .iter()
            .filter(|violation| violation.code == "RSL102")
            .collect::<Vec<_>>();
        assert_eq!(
            parser.len(),
            test_case.expected_violation_codes.len(),
            "{}",
            test_case.description
        );
        assert_eq!(
            parser[0].message, "restricted module accesses raw parser crate raw-parser",
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_renamed_workspace_library_when_checking_then_project_graph_uses_source_identity() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "aliases resolve to unique package identities despite shared library names",
        repo_files: vec![
            test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace]\nmembers = [\"crates/alpha-core\", \"crates/beta-core\", \"crates/consumer\", \"crates/direct-consumer\", \"crates/beta-consumer\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nprovider-alias = { package = \"alpha-core\", path = \"crates/alpha-core\" }\nbeta-provider = { package = \"beta-core\", path = \"crates/beta-core\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/alpha-core/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"alpha-core\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lib]\nname = \"common_api\"\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/alpha-core/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod reading;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/alpha-core/src/reading/mod.rs".to_owned(),
                contents: "pub mod main;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/alpha-core/src/reading/main/mod.rs".to_owned(),
                contents: "pub mod value;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/alpha-core/src/reading/main/value.rs".to_owned(),
                contents: "#[must_use]\npub fn value() -> usize { 1 }\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"consumer\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[dependencies]\nprovider-alias.workspace = true\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod writing;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/writing/mod.rs".to_owned(),
                contents: "pub mod main;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/writing/main/mod.rs".to_owned(),
                contents: "pub(super) mod run;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/writing/main/run.rs".to_owned(),
                contents: "use provider_alias::reading::main::value::value;\n\npub fn run() { value(); }\n"
                    .to_owned(),
            },
            test_types::RepoFile {
                path: "crates/direct-consumer/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"direct-consumer\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[dependencies]\nalpha-core = { path = \"../alpha-core\" }\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/direct-consumer/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod writing;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/direct-consumer/src/writing/mod.rs".to_owned(),
                contents: "pub mod main;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/direct-consumer/src/writing/main/mod.rs".to_owned(),
                contents: "pub(super) mod run;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/direct-consumer/src/writing/main/run.rs".to_owned(),
                contents: "use common_api::reading::main::value::value;\n\npub fn run() { value(); }\n"
                    .to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-core/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"beta-core\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lib]\nname = \"common_api\"\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-core/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod reading;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-core/src/reading/mod.rs".to_owned(),
                contents: "pub mod main;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-core/src/reading/main/mod.rs".to_owned(),
                contents: "pub mod value;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-core/src/reading/main/value.rs".to_owned(),
                contents: "pub fn value() -> usize { 1 }\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-consumer/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"beta-consumer\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[dependencies]\nbeta-provider.workspace = true\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-consumer/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod writing;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-consumer/src/writing/mod.rs".to_owned(),
                contents: "pub mod main;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-consumer/src/writing/main/mod.rs".to_owned(),
                contents: "pub(super) mod run;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/beta-consumer/src/writing/main/run.rs".to_owned(),
                contents: "use beta_provider::reading::main::value::value;\n\npub fn run() { value(); }\n"
                    .to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSS101", "RSS101"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(test_case);
        helpers::generate_lockfile(&repo_root);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        let project_codes = violations
            .iter()
            .filter(|violation| matches!(violation.code, "RSL105" | "RSS101"))
            .map(|violation| violation.code)
            .collect::<Vec<_>>();
        assert_eq!(
            project_codes, test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_same_named_external_dependency_when_checking_then_workspace_graph_stays_distinct() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "canonical dependency paths distinguish same-named Cargo packages",
        repo_files: vec![
            test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace]\nmembers = [\"crates/shared\", \"crates/consumer\"]\nexclude = [\"vendor/shared\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[patch.crates-io]\nshared = { path = \"crates/shared\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/shared/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"shared\"\nversion = \"1.0.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lib]\nname = \"local_api\"\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/shared/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod reading;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/shared/src/reading/mod.rs".to_owned(),
                contents: "pub mod main;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/shared/src/reading/main/mod.rs".to_owned(),
                contents: "pub mod value;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/shared/src/reading/main/value.rs".to_owned(),
                contents: "#[must_use]\npub fn value() -> usize { 1 }\n".to_owned(),
            },
            test_types::RepoFile {
                path: "vendor/shared/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"shared\"\nversion = \"2.0.0\"\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[lib]\nname = \"external_api\"\n".to_owned(),
            },
            test_types::RepoFile {
                path: "vendor/shared/src/lib.rs".to_owned(),
                contents: "pub mod reading { pub mod main { pub mod value { pub fn value() -> usize { 2 } } } }\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"consumer\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[dependencies]\nexternal = { package = \"shared\", path = \"../../vendor/shared\" }\npatched = { package = \"shared\", version = \"=1.0.0\", optional = true }\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod writing;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/writing/mod.rs".to_owned(),
                contents: "pub mod main;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/writing/main/mod.rs".to_owned(),
                contents: "pub(super) mod run;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/consumer/src/writing/main/run.rs".to_owned(),
                contents: "use external::reading::main::value::value as external_value;\n#[cfg(feature = \"patched\")]\nuse patched::reading::main::value::value as patched_value;\n\npub fn run() {\n    external_value();\n    #[cfg(feature = \"patched\")]\n    patched_value();\n}\n".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSS101"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(test_case);
        helpers::generate_lockfile(&repo_root);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        let project_codes = violations
            .iter()
            .filter(|violation| matches!(violation.code, "RSL104" | "RSL105" | "RSS101"))
            .map(|violation| violation.code)
            .collect::<Vec<_>>();
        assert_eq!(
            project_codes, test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_excluded_target_under_source_tree_when_checking_then_fails_closed_and_scans_file() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "an example declaration cannot hide a production module",
        repo_files: vec![
            test_types::RepoFile {
                path: "crates/example/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub mod utils;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[[example]]\nname = \"embedded\"\npath = \"src/utils.rs\"\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/src/utils.rs".to_owned(),
                contents: "fn broken(".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSL901", "RSH902"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(test_case);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        let actual = violations
            .iter()
            .filter(|violation| test_case.expected_violation_codes.contains(&violation.code))
            .map(|violation| violation.code)
            .collect::<Vec<_>>();
        assert_eq!(
            actual, test_case.expected_violation_codes,
            "{}",
            test_case.description
        );
        assert!(violations.iter().any(|violation| {
            violation.code == "RSH902"
                && violation.path == std::path::Path::new("crates/example/src/utils.rs")
        }));
    }
}

#[test]
fn given_included_and_excluded_targets_share_entry_when_checking_then_included_target_wins() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "excluded target cannot suppress a shared binary entry",
        repo_files: vec![
            test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[[bin]]\nname = \"example\"\npath = \"src/main.rs\"\n\n[[example]]\nname = \"shared\"\npath = \"src/main.rs\"\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/src/main.rs".to_owned(),
                contents: "fn broken(".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSH902"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert!(
            violations.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[0]
                    && violation.path == std::path::Path::new("crates/example/src/main.rs")
            }),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_workspace_member_path_contains_src_when_checking_then_actual_source_root_is_preserved() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "package path components cannot corrupt source-relative architecture",
        repo_files: vec![
            test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace]\nmembers = [\"packages/src/example\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n".to_owned(),
            },
            test_types::RepoFile {
                path: "packages/src/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "packages/src/example/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\n".to_owned(),
            },
            test_types::RepoFile {
                path: "packages/src/example/src/reading/models.rs".to_owned(),
                contents: "pub struct Model;\n".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSR309"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(test_case);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert!(
            violations.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[0]
                    && violation.path == std::path::Path::new("packages/src/example/src/reading")
            }),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_custom_library_or_binary_path_when_checking_then_target_fails_closed() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "custom Cargo target path is not recursively guessed",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/Cargo.toml".to_owned(),
                    contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lib]\npath = \"code/lib.rs\"\n\n[lints]\nworkspace = true\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/code/lib.rs".to_owned(),
                    contents: "#![forbid(unsafe_code)]\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSL901"],
        },
        test_types::CheckRepoTestCase {
            description: "extensionless integration target cannot disappear from scanning",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/Cargo.toml".to_owned(),
                    contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[[test]]\nname = \"extensionless\"\npath = \"tests/extensionless\"\n\n[lints]\nworkspace = true\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/extensionless".to_owned(),
                    contents: "fn main() {}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSL901"],
        },
    ];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert!(
            violations.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[0]
                    && violation.message.contains("unsupported source path")
            }),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_test_topic_without_cargo_harness_when_checking_then_file_is_not_invisible() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "conventional tests tree is checked even without a Cargo target",
        repo_files: vec![test_types::RepoFile {
            path: "crates/example/tests/orphan/test_broken.rs".to_owned(),
            contents: "fn broken(".to_owned(),
        }],
        expected_violation_codes: vec!["RSH902"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(test_case);
        let violations = helpers::check_repository(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert!(
            violations.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[0]
                    && violation.path
                        == std::path::Path::new("crates/example/tests/orphan/test_broken.rs")
            }),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_nested_role_files_and_role_free_domain_when_inventory_is_closed_then_types_are_exact() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "role containers are not domains and role-free domains remain visible",
        repo_files: vec![
            test_types::RepoFile {
                path: "crates/example/src/alpha/main/models.rs".to_owned(),
                contents: "pub struct Alpha;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/example/src/beta/feature.rs".to_owned(),
                contents: "pub struct Beta;\n".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSL305"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(test_case);
        let mut config = models::RustPolicy::default();
        config.repository.domain_paths = vec!["crates/example/src/alpha".to_owned()];
        config.repository.role_paths = vec![
            "crates/example/src/alpha/main".to_owned(),
            "crates/example/src/alpha/main/models.rs".to_owned(),
        ];
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("closed inventory configuration is valid");
        helpers::remove_temp_repo(&repo_root);
        let inventory = violations
            .iter()
            .filter(|violation| violation.code == test_case.expected_violation_codes[0])
            .map(|violation| {
                (
                    violation.code,
                    violation.path.to_string_lossy().into_owned(),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            inventory,
            vec![(
                test_case.expected_violation_codes[0],
                "crates/example/src/beta".to_owned(),
            )],
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_root_implicit_and_custom_target_packages_when_checking_then_cargo_inventory_is_used() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "Cargo workspace and target discovery",
        repo_files: vec![
            test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[package]\nname = \"root-package\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[dependencies]\nimplicit.workspace = true\n\n[lints]\nworkspace = true\n\n[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nimplicit = { path = \"crates/implicit\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n".to_owned(),
            },
            test_types::RepoFile {
                path: "src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\n".to_owned(),
            },
            test_types::RepoFile {
                path: "src/utils.rs".to_owned(),
                contents: "fn value() -> usize { 1 }\n".to_owned(),
            },
            test_types::RepoFile {
                path: "src/reading/models.rs".to_owned(),
                contents: "pub struct RootModel;\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/implicit/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"implicit\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/implicit/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/implicit/src/manager.rs".to_owned(),
                contents: "fn value() -> usize { 1 }\n".to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSR201", "RSR201", "RSR309"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let mut config = models::RustPolicy::default();
        config.repository.crate_names = vec![
            "example".to_owned(),
            "implicit".to_owned(),
            "root-package".to_owned(),
        ];
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("Cargo workspace inventory is valid");
        helpers::remove_temp_repo(&repo_root);
        assert!(
            !violations
                .iter()
                .any(|violation| violation.code == "RSL304"),
            "{}: {violations:?}",
            test_case.description
        );
        let banned = violations
            .iter()
            .filter(|violation| violation.code == test_case.expected_violation_codes[0])
            .map(|violation| violation.path.to_string_lossy().into_owned())
            .collect::<Vec<_>>();
        assert_eq!(
            vec!["RSR201"; banned.len()],
            test_case.expected_violation_codes[..2],
            "{}",
            test_case.description
        );
        assert_eq!(
            banned,
            vec![
                "crates/implicit/src/manager.rs".to_owned(),
                "src/utils.rs".to_owned(),
            ],
            "{}",
            test_case.description
        );
        assert!(
            violations.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[2]
                    && violation.path == std::path::Path::new("src/reading")
            }),
            "{}",
            test_case.description
        );
    }
}

#[cfg(unix)]
#[test]
fn given_symlink_escapes_when_checking_then_configured_source_and_dependency_paths_fail_closed() {
    use std::os::unix::fs::symlink;

    let test_cases = [test_types::CheckRepoTestCase {
        description: "canonical path containment",
        repo_files: Vec::new(),
        expected_violation_codes: vec!["RSL305", "RSL901", "RSH901", "RSL901", "RSL306"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let outside = repo_root.with_file_name(format!(
            "{}-outside",
            repo_root
                .file_name()
                .expect("fixture has a name")
                .to_string_lossy()
        ));
        std::fs::create_dir_all(outside.join("source"))
            .expect("external source fixture is writable");
        std::fs::write(outside.join("source/lib.rs"), "#![forbid(unsafe_code)]\n")
            .expect("external source is writable");
        std::fs::create_dir_all(repo_root.join("crates/example/src/escaped"))
            .expect("fixture source is writable");
        symlink(
            outside.join("source"),
            repo_root.join("crates/example/src/escaped/external"),
        )
        .expect("source symlink is writable");
        let mut config = models::RustPolicy::default();
        config.repository.domain_paths = vec!["crates/example/src/escaped/external".to_owned()];
        let configured =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("configured symlink is checked");
        assert!(
            configured
                .iter()
                .any(|violation| violation.code == test_case.expected_violation_codes[0]),
            "{}",
            test_case.description
        );

        std::fs::remove_file(repo_root.join("crates/example/src/lib.rs"))
            .expect("fixture library target is removable");
        symlink(
            outside.join("source/lib.rs"),
            repo_root.join("crates/example/src/lib.rs"),
        )
        .expect("source target symlink is writable");
        let source = helpers::check_repository(&repo_root);
        assert!(
            source.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[1]
                    && violation.message.contains("Cargo target")
            }),
            "{}",
            test_case.description
        );
        std::fs::remove_file(repo_root.join("crates/example/src/lib.rs"))
            .expect("source target symlink is removable");
        std::fs::write(
            repo_root.join("crates/example/src/lib.rs"),
            "#![forbid(unsafe_code)]\n",
        )
        .expect("fixture library target is restorable");

        std::fs::create_dir_all(repo_root.join("crates/example/src/rules"))
            .expect("nested source directory is writable");
        symlink(
            outside.join("source/lib.rs"),
            repo_root.join("crates/example/src/rules/parser.rs"),
        )
        .expect("nested source symlink is writable");
        let nested_source = helpers::check_repository(&repo_root);
        assert!(
            nested_source.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[2]
                    && violation.path == std::path::Path::new("crates/example/src/rules/parser.rs")
            }),
            "{}",
            test_case.description
        );

        std::fs::create_dir_all(outside.join("package/src"))
            .expect("external package fixture is writable");
        std::fs::write(
        outside.join("package/Cargo.toml"),
        "[package]\nname = \"escaped-package\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[lints]\nworkspace = true\n",
    )
    .expect("external package manifest is writable");
        std::fs::write(outside.join("package/src/lib.rs"), "")
            .expect("external package source is writable");
        symlink(
            outside.join("package"),
            repo_root.join("crates/escaped-package"),
        )
        .expect("package symlink is writable");
        std::fs::write(
        repo_root.join("Cargo.toml"),
        "[workspace]\nmembers = [\"crates/example\", \"crates/escaped-package\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nexample-tooling = \"0.12.0\"\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n",
    )
    .expect("fixture workspace manifest is writable");
        let package = helpers::check_repository(&repo_root);
        assert!(
            package.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[3]
                    && violation.message.contains("workspace package")
            }),
            "{}",
            test_case.description
        );

        std::fs::create_dir_all(outside.join("dependency/src"))
            .expect("external dependency fixture is writable");
        std::fs::write(
            outside.join("dependency/Cargo.toml"),
            "[package]\nname = \"escaped-dependency\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        )
        .expect("external dependency manifest is writable");
        std::fs::write(outside.join("dependency/src/lib.rs"), "")
            .expect("external dependency source is writable");
        std::fs::create_dir_all(repo_root.join("vendor")).expect("fixture vendor path is writable");
        symlink(
            outside.join("dependency"),
            repo_root.join("vendor/dependency"),
        )
        .expect("dependency symlink is writable");
        std::fs::write(
        repo_root.join("crates/example/Cargo.toml"),
        "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nescaped = { path = \"../../vendor/dependency\" }\n",
    )
    .expect("fixture manifest is writable");
        let dependency = helpers::check_repository(&repo_root);
        assert!(
            dependency
                .iter()
                .any(|violation| violation.code == test_case.expected_violation_codes[4]),
            "{}",
            test_case.description
        );
        helpers::remove_temp_repo(&repo_root);
        std::fs::remove_dir_all(outside).expect("external fixture is removable");
    }
}

#[test]
fn given_custom_parser_boundary_when_checking_then_uses_configured_policy() {
    let test_cases = [test_types::ParserConfigTestCase {
        description: "custom parser boundary",
        repo_files: vec![test_types::RepoFile {
            path: "crates/example/src/rules/_helpers/annotations.rs".to_owned(),
            contents: "use sqlparser::ast::Statement;\nuse ruff_python_ast::ModModule;\n"
                .to_owned(),
        }],
        config: models::RustPolicy {
            tooling: models::ToolingConfig {
                paths: vec!["crates/example-validator".to_owned()],
                runtime_forbidden_packages: vec![
                    "example-validator".to_owned(),
                    "example-tooling".to_owned(),
                ],
            },
            raw_parser_boundary: models::RawParserBoundaryConfig {
                packages: vec!["sqlparser".to_owned()],
                remediation: "consume shared SQL fact rows".to_owned(),
                restricted_paths: vec!["rules".to_owned()],
            },
            repository: models::RepositoryPolicyConfig::default(),
        },
        expected_violation_count: 1,
        expected_remediation: "consume shared SQL fact rows",
    }];

    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: test_case.repo_files,
            expected_violation_codes: Vec::new(),
        };
        let repo_root = helpers::write_temp_repo(&fixture);
        let violations = check_repository_with_config::check_repository_with_config(
            &repo_root,
            &test_case.config,
        )
        .expect("parser config is valid");
        helpers::remove_temp_repo(&repo_root);
        let parser_violations = violations
            .iter()
            .filter(|violation| violation.code == "RSL102")
            .collect::<Vec<_>>();
        assert_eq!(
            parser_violations.len(),
            test_case.expected_violation_count,
            "case failed: {}",
            test_case.description
        );
        assert_eq!(
            parser_violations[0].remediation, test_case.expected_remediation,
            "case failed: {}",
            test_case.description
        );
    }
}

#[test]
fn given_consumer_tooling_dependencies_when_checking_then_honors_forbidden_packages() {
    let mut config = models::RustPolicy::default();
    config.tooling.paths = vec!["crates/example-validator".to_owned()];
    config.tooling.runtime_forbidden_packages =
        vec!["example-validator".to_owned(), "example-tooling".to_owned()];
    let mut allowed_config: models::RustPolicy = models::RustPolicy::default();
    allowed_config.tooling.paths = vec!["crates/example-validator".to_owned()];
    allowed_config.tooling.runtime_forbidden_packages = Vec::new();
    let test_cases = [test_types::ToolingConfigTestCase {
        description: "consumer tooling dependency",
        repo_files: vec![test_types::RepoFile {
            path: "crates/example/Cargo.toml".to_owned(),
            contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nchecker = { package = \"example-validator\", workspace = true }\n".to_owned(),
        }, test_types::RepoFile {
            path: "Cargo.toml".to_owned(),
            contents: "[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nchecker = { package = \"example-validator\", version = \"0.1\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n".to_owned(),
        }],
        config,
        expected_code: "RSL301",
        expected_message: "crate depends on example-validator",
        expected_present: true,
    }, test_types::ToolingConfigTestCase {
            description: "unrestricted dependency is permitted",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/Cargo.toml".to_owned(),
                contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nchecker = { package = \"example-validator\", workspace = true }\n".to_owned(),
            }, test_types::RepoFile {
                path: "Cargo.toml".to_owned(),
                contents: "[workspace]\nmembers = [\"crates/example\"]\nresolver = \"2\"\n\n[workspace.package]\nedition = \"2021\"\nlicense = \"Apache-2.0\"\npublish = false\n\n[workspace.dependencies]\nchecker = { package = \"example-validator\", version = \"0.1\" }\n\n[workspace.lints.rust]\nunsafe_code = \"forbid\"\nunreachable_pub = \"deny\"\nunused_must_use = \"deny\"\n\n[workspace.lints.clippy]\nawait_holding_lock = \"deny\"\n".to_owned(),
            }],
            config: allowed_config,
            expected_code: "RSL301",
            expected_message: "crate depends on example-validator",
            expected_present: false,
    }];

    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: test_case.repo_files,
            expected_violation_codes: Vec::new(),
        };
        let repo_root = helpers::write_temp_repo(&fixture);
        let violations = check_repository_with_config::check_repository_with_config(
            &repo_root,
            &test_case.config,
        )
        .expect("tooling config is valid");
        helpers::remove_temp_repo(&repo_root);
        let present = violations.iter().any(|violation| {
            violation.code == test_case.expected_code
                && violation.message == test_case.expected_message
        });
        assert_eq!(
            present, test_case.expected_present,
            "case failed: {}",
            test_case.description
        );
    }
}

#[test]
fn given_fixture_repository_policy_when_checking_then_paths_and_thresholds_are_applied() {
    let test_cases = [test_types::RepositoryPolicyTestCase {
        description: "complete fixture repository policy",
        expected_present_code: "RSS010",
        expected_absent_codes: vec!["RSL304", "RSL305", "RSR306"],
    }];

    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/domain/main/check.rs".to_owned(),
                    contents: "pub(crate) fn check(left: usize, right: usize) -> usize {\n    left + right\n}\n"
                        .to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/domain/models.rs".to_owned(),
                    contents: "pub(crate) struct DomainModel;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/generated/models.rs".to_owned(),
                    contents: "pub(crate) struct Generated;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/generated/nested/models.rs".to_owned(),
                    contents: "pub(crate) struct Nested;\n".to_owned(),
                },
            ],
            expected_violation_codes: Vec::new(),
        };
        let repo_root = helpers::write_temp_repo_verbatim(&fixture);
        let mut config = models::RustPolicy::default();
        config.repository.crate_names = vec!["example".to_owned()];
        config.repository.domain_paths = vec!["crates/example/src/domain".to_owned()];
        config.repository.role_paths = vec![
            "crates/example/src/domain/main".to_owned(),
            "crates/example/src/domain/models.rs".to_owned(),
        ];
        config.repository.intentional_layout_paths =
            vec!["crates/example/src/generated".to_owned()];
        config.repository.thresholds.max_arguments = 1;
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("fixture repository policy is valid");
        helpers::remove_temp_repo(&repo_root);

        assert!(
            violations
                .iter()
                .any(|violation| violation.code == test_case.expected_present_code),
            "{}",
            test_case.description
        );
        assert!(
            !violations
                .iter()
                .any(|violation| test_case.expected_absent_codes.contains(&violation.code)),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_directory_named_like_role_file_when_checking_then_role_path_is_rejected() {
    let test_cases = [test_types::RepositoryPolicyTestCase {
        description: "models directory is not the models.rs role",
        expected_present_code: "RSL305",
        expected_absent_codes: Vec::new(),
    }];

    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/domain/models/generated.rs".to_owned(),
                contents: "pub(crate) struct Generated;\n".to_owned(),
            }],
            expected_violation_codes: Vec::new(),
        };
        let repo_root = helpers::write_temp_repo_verbatim(&fixture);
        let mut config = models::RustPolicy::default();
        config.repository.role_paths = vec!["crates/example/src/domain/models".to_owned()];
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("repository policy is structurally valid");
        helpers::remove_temp_repo(&repo_root);

        assert!(
            violations
                .iter()
                .any(|violation| violation.code == test_case.expected_present_code),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_source_root_as_intentional_layout_when_checking_then_broad_exclusion_is_rejected() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "source root cannot be excluded",
        repo_files: Vec::new(),
        expected_violation_codes: vec!["RSL305"],
    }];
    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let mut config = models::RustPolicy::default();
        config.repository.intentional_layout_paths = vec!["crates/example/src".to_owned()];
        let violations =
            check_repository_with_config::check_repository_with_config(&repo_root, &config)
                .expect("broad path is a repository diagnostic");
        helpers::remove_temp_repo(&repo_root);
        assert!(
            violations.iter().any(|violation| {
                violation.code == test_case.expected_violation_codes[0]
                    && violation.path == std::path::Path::new("crates/example/src")
            }),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_config_when_validating_then_fails_closed() {
    let test_cases = [
        test_types::ConfigValidationTestCase {
            description: "empty forbidden package",
            config: models::RustPolicy {
                tooling: models::ToolingConfig {
                    paths: Vec::new(),
                    runtime_forbidden_packages: vec![String::new()],
                },
                ..models::RustPolicy::default()
            },
            expected_is_error: true,
        },
        test_types::ConfigValidationTestCase {
            description: "non-canonical trailing slash path",
            config: models::RustPolicy {
                repository: models::RepositoryPolicyConfig {
                    domain_paths: vec!["crates/example/src/domain/".to_owned()],
                    ..models::RepositoryPolicyConfig::default()
                },
                ..models::RustPolicy::default()
            },
            expected_is_error: true,
        },
        test_types::ConfigValidationTestCase {
            description: "platform-independent drive path",
            config: models::RustPolicy {
                repository: models::RepositoryPolicyConfig {
                    domain_paths: vec!["C:/repository/domain".to_owned()],
                    ..models::RepositoryPolicyConfig::default()
                },
                ..models::RustPolicy::default()
            },
            expected_is_error: true,
        },
        test_types::ConfigValidationTestCase {
            description: "overlapping intentional layout paths",
            config: models::RustPolicy {
                repository: models::RepositoryPolicyConfig {
                    intentional_layout_paths: vec![
                        "crates/example/src/generated".to_owned(),
                        "crates/example/src/generated/models".to_owned(),
                    ],
                    ..models::RepositoryPolicyConfig::default()
                },
                ..models::RustPolicy::default()
            },
            expected_is_error: true,
        },
        test_types::ConfigValidationTestCase {
            description: "intentional layout overlaps declared domain",
            config: models::RustPolicy {
                repository: models::RepositoryPolicyConfig {
                    domain_paths: vec!["crates/example/src/domain".to_owned()],
                    intentional_layout_paths: vec!["crates/example/src/domain/generated".to_owned()],
                    ..models::RepositoryPolicyConfig::default()
                },
                ..models::RustPolicy::default()
            },
            expected_is_error: true,
        },
    ];

    for test_case in test_cases {
        assert_eq!(
            test_case.config.validate().is_err(),
            test_case.expected_is_error,
            "case failed: {}",
            test_case.description
        );
        assert!(
            check_repository_with_config::check_repository_with_config(
                std::path::Path::new("."),
                &test_case.config,
            )
            .is_err(),
            "public checker entry must reject invalid config: {}",
            test_case.description
        );
    }
}
