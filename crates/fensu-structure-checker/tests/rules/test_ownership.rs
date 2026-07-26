//! Transitive domain-ownership policy over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_helper_consumers_when_checking_then_reports_misowned_modules() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "configuration helper used only by init is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/configuration/_helpers/discovery.rs".to_owned(),
                    contents: "pub(crate) fn discover() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/init/main/init.rs".to_owned(),
                    contents: "use crate::configuration::_helpers::discovery::discover;\n\npub(super) fn init() -> usize {\n    discover()\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR310", "RSL101"],
        },
        test_types::CheckRepoTestCase {
            description: "helper moved to its init owner is accepted",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/init/_helpers/discovery.rs".to_owned(),
                    contents: "pub(crate) fn discover() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/init/main/init.rs".to_owned(),
                    contents: "use crate::init::_helpers::discovery::discover;\n\npub(super) fn init() -> usize {\n    discover()\n}\n"
                        .to_owned(),
                },
            ],
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
