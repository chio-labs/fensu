//! Consumer configuration behavior over fixture repositories.

use crate::helpers;
use crate::test_types;
use fensu_structure_checker::models;
use fensu_structure_checker::rules::main::{check_repository, check_repository_with_config};

#[test]
fn given_explicit_fensu_defaults_when_checking_then_diagnostics_are_unchanged() {
    let test_cases = [test_types::ConfigCompatibilityTestCase {
        description: "default compatibility",
        repo_files: vec![test_types::RepoFile {
            path: "crates/example/src/rules/_helpers/annotations.rs".to_owned(),
            contents: "use ruff_python_ast::ModModule;\n".to_owned(),
        }],
        expected_equal: true,
    }];

    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: test_case.repo_files,
            expected_violation_codes: Vec::new(),
        };
        let repo_root = helpers::write_temp_repo(&fixture);
        let implicit = check_repository::check_repository(&repo_root);
        let explicit = check_repository_with_config::check_repository_with_config(
            &repo_root,
            &models::CheckerConfig::default(),
        )
        .expect("explicit defaults are valid");
        helpers::remove_temp_repo(&repo_root);
        assert_eq!(
            implicit == explicit,
            test_case.expected_equal,
            "case failed: {}",
            test_case.description
        );
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
        config: models::CheckerConfig {
            schema_version: 1,
            tooling: models::ToolingConfig {
                package: "sqlbuild-structure-checker".to_owned(),
                runtime_forbidden_packages: vec![
                    "sqlbuild-structure-checker".to_owned(),
                    "fensu-structure-checker".to_owned(),
                ],
            },
            raw_parser_boundary: models::RawParserBoundaryConfig {
                packages: vec!["sqlparser".to_owned()],
                remediation: "consume shared SQL fact rows".to_owned(),
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
fn given_consumer_tooling_dependencies_when_checking_then_blocks_every_shared_checker() {
    let mut config = models::CheckerConfig::default();
    config.tooling.package = "sqlbuild-structure-checker".to_owned();
    config.tooling.runtime_forbidden_packages = vec![
        "sqlbuild-structure-checker".to_owned(),
        "fensu-structure-checker".to_owned(),
    ];
    let test_cases = [test_types::ToolingConfigTestCase {
        description: "consumer tooling dependency",
        repo_files: vec![test_types::RepoFile {
            path: "crates/example/Cargo.toml".to_owned(),
            contents: "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition.workspace = true\nlicense.workspace = true\npublish.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\nchecker = { package = \"sqlbuild-structure-checker\", workspace = true }\n".to_owned(),
        }],
        config,
        expected_code: "RSL301",
        expected_message: "crate depends on sqlbuild-structure-checker",
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
        assert!(
            violations.iter().any(|violation| {
                violation.code == test_case.expected_code
                    && violation.message == test_case.expected_message
            }),
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
        let mut config = models::CheckerConfig::default();
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
        let mut config = models::CheckerConfig::default();
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
fn given_invalid_config_when_validating_then_fails_closed() {
    let test_cases = [
        test_types::ConfigValidationTestCase {
            description: "unsupported schema",
            config: models::CheckerConfig {
                schema_version: 2,
                ..models::CheckerConfig::default()
            },
            expected_is_error: true,
        },
        test_types::ConfigValidationTestCase {
            description: "empty tooling package",
            config: models::CheckerConfig {
                tooling: models::ToolingConfig {
                    package: String::new(),
                    runtime_forbidden_packages: Vec::new(),
                },
                ..models::CheckerConfig::default()
            },
            expected_is_error: true,
        },
        test_types::ConfigValidationTestCase {
            description: "non-canonical trailing slash path",
            config: models::CheckerConfig {
                repository: models::RepositoryPolicyConfig {
                    domain_paths: vec!["crates/example/src/domain/".to_owned()],
                    ..models::RepositoryPolicyConfig::default()
                },
                ..models::CheckerConfig::default()
            },
            expected_is_error: true,
        },
        test_types::ConfigValidationTestCase {
            description: "platform-independent drive path",
            config: models::CheckerConfig {
                repository: models::RepositoryPolicyConfig {
                    domain_paths: vec!["C:/repository/domain".to_owned()],
                    ..models::RepositoryPolicyConfig::default()
                },
                ..models::CheckerConfig::default()
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
