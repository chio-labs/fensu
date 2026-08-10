use crate::analyzer::AnalyzerId;
use crate::check::_helpers::policy::{check_identity, path_matches};
use crate::check::models::CheckIdentityRequest;
use crate::configuration::main::resolve_target_root::resolve_target_root;
use crate::mapping::_helpers::cache::generation;
use crate::mapping::models::SourceSnapshot;
use crate::models::Config;
use crate::tests::test_types::{
    CacheIdentityFramingTestCase, EscapingSymlinkTargetTestCase, MapCacheIdentityTestCase,
    MissingSuffixSymlinkTargetTestCase, PathMatchTestCase, TargetRootRepresentationTestCase,
    WebTestLayoutIdentityTestCase,
};

#[cfg(unix)]
#[test]
fn given_internal_symlink_and_missing_suffix_when_resolving_then_appends_to_canonical_ancestor() {
    use std::os::unix::fs::symlink;

    let test_cases = [MissingSuffixSymlinkTargetTestCase {
        description: "missing suffix remains under canonical in-repository target",
        configured: "alias/missing/package",
        expected_root: "real/missing/package",
    }];
    let repository = tempfile::tempdir().expect("symlink target repository");
    std::fs::create_dir(repository.path().join("real")).expect("real target directory");
    symlink(
        repository.path().join("real"),
        repository.path().join("alias"),
    )
    .expect("internal target alias");
    for test_case in &test_cases {
        let resolved = resolve_target_root(repository.path(), test_case.configured)
            .expect("internal alias target resolves");
        let canonical_repository =
            dunce::canonicalize(repository.path()).expect("repository canonicalizes");
        let relative = resolved
            .strip_prefix(canonical_repository)
            .expect("resolved target remains in repository")
            .to_string_lossy()
            .replace('\\', "/");

        assert_eq!(
            relative, test_case.expected_root,
            "{}",
            test_case.description
        );
    }
}

#[cfg(unix)]
#[test]
fn given_escaping_symlink_and_missing_suffix_when_resolving_then_rejects_canonical_escape() {
    use std::os::unix::fs::symlink;

    let test_cases = [EscapingSymlinkTargetTestCase {
        description: "missing suffix below external alias cannot use lexical confinement",
        configured: "alias/missing/package",
        expected_error: "must not escape the repository",
    }];
    let repository = tempfile::tempdir().expect("symlink target repository");
    let external = tempfile::tempdir().expect("external target directory");
    symlink(external.path(), repository.path().join("alias")).expect("external target alias");
    for test_case in &test_cases {
        let error = resolve_target_root(repository.path(), test_case.configured)
            .expect_err("external alias target is rejected");

        assert!(
            error.contains(test_case.expected_error),
            "{}: {error}",
            test_case.description
        );
    }
}

#[test]
fn given_repository_and_target_when_resolving_then_both_use_dunce_canonical_representation() {
    let test_cases = [
        TargetRootRepresentationTestCase {
            description: "legacy dot root uses repository canonical representation",
            configured: ".",
            expected_root: ".",
        },
        TargetRootRepresentationTestCase {
            description: "non-dot root uses matching canonical representation",
            configured: "frontend",
            expected_root: "frontend",
        },
    ];
    let repository = tempfile::tempdir().expect("target root repository");
    for test_case in &test_cases {
        let target = repository.path().join(test_case.configured);
        std::fs::create_dir_all(&target).expect("target root fixture");

        let resolved = resolve_target_root(repository.path(), test_case.configured)
            .expect("target root resolves");
        let canonical_repository =
            dunce::canonicalize(repository.path()).expect("repository root canonicalizes");
        let expected = dunce::canonicalize(repository.path().join(test_case.expected_root))
            .expect("target root canonicalizes");
        let relative = resolved
            .strip_prefix(canonical_repository)
            .expect("target remains under repository");
        let actual_root = relative
            .to_str()
            .filter(|value| !value.is_empty())
            .unwrap_or(".")
            .replace('\\', "/");

        assert_eq!(
            actual_root, test_case.expected_root,
            "{}",
            test_case.description
        );
        assert_eq!(resolved, expected, "{}", test_case.description);
    }
}

#[test]
fn given_ambiguous_target_field_concatenations_when_fingerprinting_then_identity_is_framed() {
    let test_cases = [
        CacheIdentityFramingTestCase {
            description: "target and root boundary cannot collide",
            first_analyzer: AnalyzerId::Python,
            first_target: "ab",
            first_root: "c",
            second_analyzer: AnalyzerId::Python,
            second_target: "a",
            second_root: "bc",
            expected_equal: false,
        },
        CacheIdentityFramingTestCase {
            description: "analyzer contracts produce distinct identities",
            first_analyzer: AnalyzerId::Python,
            first_target: "web",
            first_root: "root",
            second_analyzer: AnalyzerId::TypeScript,
            second_target: "web",
            second_root: "root",
            expected_equal: false,
        },
    ];
    let repository = tempfile::tempdir().expect("cache identity repository");
    for test_case in &test_cases {
        let first = Config {
            analyzer: test_case.first_analyzer,
            target: Some(test_case.first_target.to_owned()),
            target_root: test_case.first_root.to_owned(),
            raw: b"same config source".to_vec(),
            ..Config::default()
        };
        let second = Config {
            analyzer: test_case.second_analyzer,
            target: Some(test_case.second_target.to_owned()),
            target_root: test_case.second_root.to_owned(),
            raw: b"same config source".to_vec(),
            ..Config::default()
        };

        let first_identity = check_identity(CheckIdentityRequest {
            root: repository.path(),
            project_root: repository.path(),
            config: &first,
            sources: &[],
            project_inputs: &[],
            warnings: false,
        })
        .expect("first check identity");
        let second_identity = check_identity(CheckIdentityRequest {
            root: repository.path(),
            project_root: repository.path(),
            config: &second,
            sources: &[],
            project_inputs: &[],
            warnings: false,
        })
        .expect("second check identity");

        assert_eq!(
            first_identity == second_identity,
            test_case.expected_equal,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_web_test_layout_change_when_fingerprinting_then_check_identity_changes() {
    let test_cases = [WebTestLayoutIdentityTestCase {
        description: "mirrored and colocated layouts have distinct identities",
        first_layout: crate::models::TestLayout::Mirrored,
        second_layout: crate::models::TestLayout::Colocated,
        expected_equal: false,
    }];
    let repository = tempfile::tempdir().expect("cache identity repository");
    for test_case in test_cases {
        let first = Config {
            analyzer: AnalyzerId::TypeScript,
            target: Some("web".to_owned()),
            test_layout: test_case.first_layout,
            raw: b"same config source".to_vec(),
            ..Config::default()
        };
        let second = Config {
            test_layout: test_case.second_layout,
            ..first.clone()
        };
        let identity = |config| {
            check_identity(CheckIdentityRequest {
                root: repository.path(),
                project_root: repository.path(),
                config,
                sources: &[],
                project_inputs: &[],
                warnings: false,
            })
            .expect("check identity")
        };

        assert_eq!(
            identity(&first) == identity(&second),
            test_case.expected_equal,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_analyzer_and_path_boundaries_when_mapping_then_cache_identity_is_framed() {
    let test_cases = [MapCacheIdentityTestCase {
        description: "mapping path and analyzer cache identities cannot collide",
        expected_path_identity_equal: false,
        expected_analyzer_identity_equal: false,
    }];
    let first = SourceSnapshot {
        path: "ab".into(),
        relative_path: "ab".to_owned(),
        import_root_identity: "root".to_owned(),
        module_name: "c".to_owned(),
        source: Vec::new(),
        source_fingerprint: "source".to_owned(),
    };
    let second = SourceSnapshot {
        path: "a".into(),
        relative_path: "a".to_owned(),
        import_root_identity: "root".to_owned(),
        module_name: "bc".to_owned(),
        source: Vec::new(),
        source_fingerprint: "source".to_owned(),
    };

    let first_generation = generation(AnalyzerId::Python, &[first]);
    let second_generation = generation(AnalyzerId::Python, &[second]);
    let other_analyzer = generation(
        AnalyzerId::TypeScript,
        &[SourceSnapshot {
            path: "ab".into(),
            relative_path: "ab".to_owned(),
            import_root_identity: "root".to_owned(),
            module_name: "c".to_owned(),
            source: Vec::new(),
            source_fingerprint: "source".to_owned(),
        }],
    );

    for test_case in &test_cases {
        assert_eq!(
            first_generation.file_identities == second_generation.file_identities,
            test_case.expected_path_identity_equal,
            "{}",
            test_case.description
        );
        assert_eq!(
            first_generation.file_identities == other_analyzer.file_identities,
            test_case.expected_analyzer_identity_equal,
            "{}",
            test_case.description
        );
        assert_eq!(
            first_generation.project_identity == other_analyzer.project_identity,
            test_case.expected_analyzer_identity_equal,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_recursive_include_when_matching_nested_path_then_matches() {
    let test_cases = [
        PathMatchTestCase {
            description: "recursive test include matches a nested test",
            path: "tests/unit/dagster_example/defs/assets/example/test_asset.py",
            pattern: "tests/unit/**",
            expected_matches: true,
        },
        PathMatchTestCase {
            description: "single segment followed by recursion matches a nested runtime file",
            path: "dagster_example/defs/assets/example/main.py",
            pattern: "dagster_example/*/**",
            expected_matches: true,
        },
    ];

    for test_case in &test_cases {
        assert_eq!(
            path_matches(test_case.path, test_case.pattern),
            test_case.expected_matches,
            "{}",
            test_case.description
        );
    }
}
