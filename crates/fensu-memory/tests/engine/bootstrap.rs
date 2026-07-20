//! Safe and idempotent canonical memory bootstrap behavior.

use std::fs;

use fensu_memory::source::main::bootstrap_memory::bootstrap_memory;

use crate::dependencies::helpers;
use crate::test_types::{FixtureFile, MemoryBootstrapTestCase};

#[test]
fn given_empty_repository_when_bootstrapping_twice_then_structure_and_ignore_are_idempotent() {
    let test_cases = [MemoryBootstrapTestCase {
        description: "empty repository creates complete canonical state once",
        expected_gitignore: "# Fensu\n.fensu/memory/\n",
        expected_error: "",
        expected_marker_exists: true,
        expected_target: ".ai/_archive/knowledge/repo/skills",
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[]);

        bootstrap_memory(&root).expect("first bootstrap succeeds");
        bootstrap_memory(&root).expect("second bootstrap succeeds");

        assert_eq!(
            root.join(".fensu/memory/.bootstrapped").is_file(),
            test_case.expected_marker_exists,
            "{}",
            test_case.description
        );
        assert!(
            root.join(".ai/tasks/in-progress").is_dir(),
            "{}",
            test_case.description
        );
        assert!(
            root.join(test_case.expected_target).is_dir(),
            "{}",
            test_case.description
        );
        assert_eq!(
            fs::read_to_string(root.join(".gitignore")).expect("gitignore is readable"),
            test_case.expected_gitignore,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("bootstrap repository is removable");
    }
}

#[test]
fn given_existing_gitignore_without_newline_when_bootstrapping_then_entry_is_appended_once() {
    let test_cases = [MemoryBootstrapTestCase {
        description: "existing gitignore receives one separated Fensu block",
        expected_gitignore: "target/\n# Fensu\n.fensu/memory/\n",
        expected_error: "",
        expected_marker_exists: true,
        expected_target: "",
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[FixtureFile {
            path: ".gitignore",
            contents: b"target/",
        }]);

        bootstrap_memory(&root).expect("bootstrap succeeds");
        bootstrap_memory(&root).expect("repeated bootstrap succeeds");

        assert_eq!(
            fs::read_to_string(root.join(".gitignore")).expect("gitignore is readable"),
            test_case.expected_gitignore,
            "{}",
            test_case.description
        );
        assert_eq!(
            root.join(".fensu/memory/.bootstrapped").is_file(),
            test_case.expected_marker_exists,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("bootstrap repository is removable");
    }
}

#[test]
fn given_noncanonical_existing_source_when_bootstrapping_then_no_state_is_created() {
    let test_cases = [MemoryBootstrapTestCase {
        description: "noncanonical source blocks migration and all generated state",
        expected_gitignore: "",
        expected_error: "Existing .ai content is not canonical",
        expected_marker_exists: false,
        expected_target: "",
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[FixtureFile {
            path: ".ai/orphan.md",
            contents: b"# Orphan\n",
        }]);

        let error = bootstrap_memory(&root).expect_err("conflicting source blocks bootstrap");

        assert!(
            error.contains(test_case.expected_error),
            "{}",
            test_case.description
        );
        assert_eq!(
            root.join(".fensu/memory/.bootstrapped").exists(),
            test_case.expected_marker_exists,
            "{}",
            test_case.description
        );
        assert!(
            !root.join(".gitignore").exists(),
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("conflict repository is removable");
    }
}

#[cfg(unix)]
#[test]
fn given_symlinked_gitignore_when_bootstrapping_then_target_is_not_followed() {
    use std::os::unix::fs::symlink;

    let test_cases = [MemoryBootstrapTestCase {
        description: "symlinked gitignore is rejected without modifying its target",
        expected_gitignore: "",
        expected_error: "Memory bootstrap could not open",
        expected_marker_exists: false,
        expected_target: "keep\n",
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[FixtureFile {
            path: "outside-ignore",
            contents: b"keep\n",
        }]);
        symlink(root.join("outside-ignore"), root.join(".gitignore")).expect("symlink fixture");

        let error = bootstrap_memory(&root).expect_err("symlinked gitignore is rejected");

        assert!(
            error.contains(test_case.expected_error),
            "{}",
            test_case.description
        );
        assert_eq!(
            fs::read_to_string(root.join("outside-ignore")).expect("target is readable"),
            test_case.expected_target,
            "{}",
            test_case.description
        );
        assert_eq!(
            root.join(".fensu/memory/.bootstrapped").exists(),
            test_case.expected_marker_exists,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("symlink repository is removable");
    }
}
