//! Comment tokens and documentation runs retain lexical source locations.

use crate::{helpers, test_types};

#[test]
fn given_comment_tokens_when_checking_then_reports_each_plain_comment_once() {
    let test_cases = [
        test_types::CommentTestCase {
            description: "multiline nested block reports only its start and preserves following lines",
            source: "fn value() { /* outer\n/* nested */\nend */ } // visible\n",
            expected_locations: &[("RSH002", 1), ("RSH002", 3)],
        },
        test_types::CommentTestCase {
            description: "trailing line comment",
            source: "fn value() {} // explanation\n",
            expected_locations: &[("RSH002", 1)],
        },
        test_types::CommentTestCase {
            description: "inline and standalone blocks with nested comments",
            source: "/* first */\nfn value() { /* outer /* inner */ end */ } /* last */\n",
            expected_locations: &[("RSH002", 1), ("RSH002", 2), ("RSH002", 2)],
        },
        test_types::CommentTestCase {
            description: "four slashes and empty or extra-star blocks are plain",
            source: "//// plain\n/**/ /*** plain */\n",
            expected_locations: &[("RSH002", 1), ("RSH002", 2), ("RSH002", 2)],
        },
        test_types::CommentTestCase {
            description: "all four doc forms are allowed on one line",
            source: "//! inner\n\n/*! inner */\n/// outer\nfn value() {}\n/** outer */\nfn other() {}\n",
            expected_locations: &[],
        },
        test_types::CommentTestCase {
            description: "doc blocks and adjacent line docs count their lines",
            source: "/*! inner\nsecond */\n/** outer\nsecond */\nfn value() {}\n/// first\n/// second\nfn other() {}",
            expected_locations: &[("RSH001", 1), ("RSH001", 3), ("RSH001", 6)],
        },
        test_types::CommentTestCase {
            description: "ordinary strings byte strings and escaped quotes hide markers",
            source: r#"fn value() { let text = "\" // /* hidden */"; let bytes = b"// /* hidden */"; } // visible"#,
            expected_locations: &[("RSH002", 1)],
        },
        test_types::CommentTestCase {
            description: "raw strings with arbitrary hashes and interior quotes hide markers",
            source: r#####"fn value() { let a = r"//"; let b = r###""## /* hidden */ //"###; let c = br##""# // /* hidden */"##; } /* visible */"#####,
            expected_locations: &[("RSH002", 1)],
        },
        test_types::CommentTestCase {
            description: "C strings and raw C strings hide comment markers",
            source: r#####"fn value() { let a = c"// /* hidden */"; let b = cr###""## // /* hidden */"###; } // visible"#####,
            expected_locations: &[("RSH002", 1)],
        },
        test_types::CommentTestCase {
            description: "characters and byte characters do not swallow following comments",
            source: r#"fn value() { let a = '/'; let b = b'/'; let c = '\''; let d = b'\''; let e = '\u{2f}'; let f = 'é'; } // visible"#,
            expected_locations: &[("RSH002", 1)],
        },
        test_types::CommentTestCase {
            description: "lifetimes and labels next to comments remain tokens",
            source: "fn value<'a, 'é>(a: &'a str, b: &'é str) { 'label: loop { break 'label; } } // first\nfn other<'a // second\n>(a: &'a str) {}",
            expected_locations: &[("RSH002", 1), ("RSH002", 2)],
        },
        test_types::CommentTestCase {
            description: "multiline literal contents cannot create doc runs",
            source: "fn value() { let text = r#\"\n/// hidden\n/// hidden\n\"#; }\n// visible",
            expected_locations: &[("RSH002", 5)],
        },
        test_types::CommentTestCase {
            description: "nested plain markers in a doc block belong to the doc token",
            source: "/** doc /* nested */ */\nfn value() {}",
            expected_locations: &[],
        },
        test_types::CommentTestCase {
            description: "raw identifiers and identifiers ending in r are not raw prefixes",
            source: "fn value() { let r#value = 1; let identifier = \"// hidden\"; } // visible",
            expected_locations: &[("RSH002", 1)],
        },
    ];
    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/values/_helpers/value.rs".to_owned(),
                contents: test_case.source.to_owned(),
            }],
            expected_violation_codes: vec![],
        };
        let root = helpers::write_temp_repo(&fixture);
        let violations = helpers::check_repository(&root);
        helpers::remove_temp_repo(&root);
        let locations: Vec<_> = violations
            .iter()
            .filter(|violation| matches!(violation.code, "RSH001" | "RSH002"))
            .map(|violation| (violation.code, violation.line.expect("comment start line")))
            .collect();
        assert_eq!(
            locations, test_case.expected_locations,
            "{}",
            test_case.description
        );
    }
}
