use std::fs;

use fensu_rust::engine::main::analyze_repository::analyze_repository;
use fensu_rust::{CACHE_CONTRACT_VERSION, FACT_SCHEMA_VERSION, PARSER_CONTRACT_VERSION};

use crate::test_types::{EngineTestCase, RustFactsEngineTestCase};

#[test]
fn given_minimal_workspace_when_analyzing_then_engine_returns_owned_diagnostics() {
    let test_cases = [EngineTestCase {
        description: "minimal workspace returns owned diagnostics and stable contracts",
        expected_cache_contract: "rust-rules-v5",
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

        let analysis = analyze_repository(temporary.path(), None, &[]).expect("analysis succeeds");
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

#[test]
fn given_rust_declarations_and_use_when_analyzing_then_owned_facts_are_versioned_and_resolved() {
    let test_cases = [RustFactsEngineTestCase {
        description: "declarations and uses become versioned owned facts",
        expected_schema: FACT_SCHEMA_VERSION,
        expected_parser: PARSER_CONTRACT_VERSION,
        expected_crate: "example-package",
        expected_item_kind: "struct",
        expected_visibility: "public",
        expected_derive: "Clone",
        expected_resolution: "resolved",
        expected_target: "src/nested/mod.rs",
        expected_main_module: &["example_package", "main"],
        expected_library_target: "src/lib.rs",
        expected_binary_resolution: "crate",
        expected_lock_created: false,
    }];
    for test_case in test_cases {
        let temporary = tempfile::tempdir().expect("temporary workspace");
        fs::write(
            temporary.path().join("Cargo.toml"),
            "[package]\nname = \"example-package\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        )
        .expect("manifest");
        fs::create_dir_all(temporary.path().join("src/nested")).expect("source directory");
        fs::write(
            temporary.path().join("src/lib.rs"),
            "pub mod nested;\npub use crate::nested::value;\npub use crate::LibraryType;\npub struct LibraryType;\n#[derive(Clone)]\npub struct Item;\npub trait Contract {}\nimpl Contract for Item {}\n",
        )
        .expect("library source");
        fs::write(
            temporary.path().join("src/nested/mod.rs"),
            "pub fn value() -> usize { 1 }\n",
        )
        .expect("module source");
        fs::write(
            temporary.path().join("src/main.rs"),
            "mod binary_nested;\nuse crate::binary_nested::Thing;\nfn main() {}\n",
        )
        .expect("binary source");
        fs::write(
            temporary.path().join("src/binary_nested.rs"),
            "pub struct Thing;\n",
        )
        .expect("binary child source");

        let analysis = analyze_repository(temporary.path(), None, &[]).expect("analysis succeeds");
        let library = analysis
            .facts
            .files
            .iter()
            .find(|file| file.path == "src/lib.rs")
            .expect("library facts");
        let item = library
            .items
            .iter()
            .find(|item| item.name.as_deref() == Some("Item"))
            .expect("struct fact");
        let use_fact = library
            .uses
            .iter()
            .find(|use_fact| use_fact.authored_parts == ["crate", "nested", "value"])
            .expect("nested use fact");
        let library_use = library
            .uses
            .iter()
            .find(|use_fact| use_fact.authored_parts == ["crate", "LibraryType"])
            .expect("library-root use fact");
        let main = analysis
            .facts
            .files
            .iter()
            .find(|file| file.path == "src/main.rs")
            .expect("binary facts");
        let binary_use = main.uses.first().expect("binary use fact");

        assert_eq!(
            analysis.facts.schema_version, test_case.expected_schema,
            "{}",
            test_case.description
        );
        assert_eq!(
            analysis.facts.parser_contract, test_case.expected_parser,
            "{}",
            test_case.description
        );
        assert_eq!(
            analysis.facts.crates[0].name, test_case.expected_crate,
            "{}",
            test_case.description
        );
        assert_eq!(
            item.kind, test_case.expected_item_kind,
            "{}",
            test_case.description
        );
        assert_eq!(
            item.visibility, test_case.expected_visibility,
            "{}",
            test_case.description
        );
        assert_eq!(
            item.derives,
            [test_case.expected_derive],
            "{}",
            test_case.description
        );
        assert_eq!(
            use_fact.resolution, test_case.expected_resolution,
            "{}",
            test_case.description
        );
        assert_eq!(
            use_fact.target_path.as_deref(),
            Some(test_case.expected_target),
            "{}",
            test_case.description
        );
        assert_eq!(
            main.module_parts, test_case.expected_main_module,
            "{}",
            test_case.description
        );
        assert_ne!(
            library.module_parts, main.module_parts,
            "{}",
            test_case.description
        );
        assert_eq!(
            library_use.target_path.as_deref(),
            Some(test_case.expected_library_target),
            "{}",
            test_case.description
        );
        assert_eq!(
            binary_use.resolution, test_case.expected_binary_resolution,
            "{}",
            test_case.description
        );
        assert_eq!(binary_use.target_path, None, "{}", test_case.description);
        assert_eq!(
            temporary.path().join("Cargo.lock").exists(),
            test_case.expected_lock_created,
            "{}",
            test_case.description
        );
    }
}
