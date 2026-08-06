use crate::check::_helpers::policy::path_matches;
use crate::tests::test_types::PathMatchTestCase;

#[test]
fn given_recursive_include_when_matching_nested_path_then_matches() {
    let test_cases = [
        PathMatchTestCase {
            description: "recursive test include matches a nested test",
            path: "tests/unit/dagster_mustard/defs/assets/example/test_asset.py",
            pattern: "tests/unit/**",
            expected_matches: true,
        },
        PathMatchTestCase {
            description: "single segment followed by recursion matches a nested runtime file",
            path: "dagster_mustard/defs/assets/example/main.py",
            pattern: "dagster_mustard/*/**",
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
