//! Git visibility through linked-worktree gitdir files.

use std::fs;

use strata_memory::source::main::discover_memory::discover_memory;
use strata_memory::source::types::GitTracking;

use crate::helpers;
use crate::test_types::{FixtureFile, GitWorktreeTestCase};

#[test]
fn given_linked_worktree_when_discovering_then_resolves_real_gitdir_and_ignore_sources() {
    let test_cases = [GitWorktreeTestCase {
        description: "classifies worktree ignores through a linked gitdir file",
        basename: "20260718T120000_000006Z__NOTE-linked-worktree.md",
        expected_document_count: 1,
        expected_tracking: GitTracking::IgnoredRepository,
    }];
    for test_case in &test_cases {
        let root = helpers::write_temp_tree(
            &[],
            &[FixtureFile {
                path: "README.md",
                contents: "fixture\n",
            }],
        );
        helpers::run_git(&root, &["init", "--quiet"]);
        helpers::run_git(&root, &["add", "README.md"]);
        helpers::run_git(
            &root,
            &[
                "-c",
                "user.name=Strata Test",
                "-c",
                "user.email=strata@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "fixture",
            ],
        );
        let worktree = root.with_extension("linked-worktree");
        let worktree_value = worktree.to_string_lossy().into_owned();
        helpers::run_git(
            &root,
            &[
                "worktree",
                "add",
                "--quiet",
                "-b",
                "memory-fixture",
                &worktree_value,
            ],
        );
        let note = worktree
            .join(".ai/knowledge/repo/notes")
            .join(test_case.basename);
        fs::create_dir_all(note.parent().expect("linked note has a parent"))
            .expect("linked note parent is writable");
        fs::write(&note, "# Linked worktree\n").expect("linked note is writable");
        fs::write(worktree.join(".gitignore"), ".ai/\n").expect("worktree ignore is writable");

        let result = discover_memory(&worktree);

        assert_eq!(
            result.documents.len(),
            test_case.expected_document_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.documents[0].git_tracking, test_case.expected_tracking,
            "{}",
            test_case.description
        );
        helpers::run_git(&root, &["worktree", "remove", "--force", &worktree_value]);
        helpers::remove_temp_tree(&root);
    }
}
