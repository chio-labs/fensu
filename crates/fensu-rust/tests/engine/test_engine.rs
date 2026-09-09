use std::fs;

use fensu_rust::{analyze_repository, CACHE_CONTRACT_VERSION, PARSER_CONTRACT_VERSION};

use crate::test_types::EngineTestCase;

#[test]
fn given_minimal_workspace_when_analyzing_then_engine_returns_owned_diagnostics() {
    let test_cases = [EngineTestCase {
        description: "minimal workspace returns owned diagnostics and stable contracts",
        expected_cache_contract: "rust-structure-policy-v1",
        expected_diagnostics: true,
        expected_lock_created: false,
        expected_parser_contract: "rust-syn-workspace-v1",
    }];
    for test_case in test_cases {
        let temporary = tempfile::tempdir().expect("temporary workspace");
        fs::write(
            temporary.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        )
        .expect("manifest");
        fs::create_dir(temporary.path().join("src")).expect("source directory");
        fs::write(
            temporary.path().join("src/lib.rs"),
            "pub fn value() -> usize { 1 }\n",
        )
        .expect("source");

        let analysis = analyze_repository(temporary.path(), None).expect("analysis succeeds");
        let diagnostics_are_owned = analysis
            .diagnostics
            .iter()
            .all(|diagnostic| !diagnostic.code.is_empty() && !diagnostic.message.is_empty());

        assert_eq!(
            diagnostics_are_owned, test_case.expected_diagnostics,
            "{}",
            test_case.description
        );
        assert_eq!(
            PARSER_CONTRACT_VERSION, test_case.expected_parser_contract,
            "{}",
            test_case.description
        );
        assert_eq!(
            CACHE_CONTRACT_VERSION, test_case.expected_cache_contract,
            "{}",
            test_case.description
        );
        assert_eq!(
            temporary.path().join("Cargo.lock").exists(),
            test_case.expected_lock_created,
            "{}",
            test_case.description
        );
    }
}
