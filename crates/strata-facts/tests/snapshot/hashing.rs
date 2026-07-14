//! Parallel content hashing behavior.

use strata_facts::snapshot::main::hash_files::hash_files;

use crate::helpers;
use crate::test_types;

#[test]
fn given_readable_files_when_hashing_then_returns_sha256_hex() {
    let test_cases = [
        test_types::HashTestCase {
            description: "hashes raw bytes to lowercase sha256 hex",
            contents: Some("x = 1\n"),
            expected_hash: Some("9e26bf369911c45c243c684147b23fc9e1dcfcf257d299a1c632016a6fcd33f4"),
        },
        test_types::HashTestCase {
            description: "hashes an empty file to the empty digest",
            contents: Some(""),
            expected_hash: Some("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        },
    ];
    for test_case in test_cases {
        let contents = test_case.contents.expect("readable cases define contents");
        let base = helpers::write_temp_tree(
            &[test_types::FixtureFile {
                path: "root/module.py",
                contents,
            }],
            &[],
        );
        let target = base.join("root/module.py");

        let hashes = hash_files(&[target]);

        let actual = hashes.first().expect("one hash row is returned");
        assert_eq!(
            actual,
            &test_case.expected_hash.map(str::to_owned),
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&base);
    }
}

#[test]
fn given_missing_file_when_hashing_then_returns_none() {
    let test_cases = [test_types::HashTestCase {
        description: "reports unreadable files as missing hashes",
        contents: None,
        expected_hash: None,
    }];
    for test_case in test_cases {
        let base = helpers::write_temp_tree(&[], &[]);
        let target = base.join("root/module.py");

        let hashes = hash_files(&[target]);

        let actual = hashes.first().expect("one hash row is returned");
        assert_eq!(
            actual,
            &test_case.expected_hash.map(str::to_owned),
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&base);
    }
}
