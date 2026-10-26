//! Proc-macro crate roots allow thin macro entries and nothing else.

use crate::helpers;
use crate::test_types;

#[test]
fn given_proc_macro_roots_when_checking_then_only_thin_entries_are_allowed() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "derive, attribute, and function-like thin entries pass",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "use syn::{parse_macro_input, DeriveInput, ItemFn};\n\n/// Derive the shape trait.\n#[proc_macro_derive(Shape, attributes(shape))]\npub fn derive_shape(input: TokenStream) -> TokenStream {\n    let input = parse_macro_input!(input as DeriveInput);\n    shapes::derive_shape(&input).into()\n}\n\n/// Trace a function.\n#[proc_macro_attribute]\npub fn traced(attribute: TokenStream, item: TokenStream) -> TokenStream {\n    let item = parse_macro_input!(item as ItemFn);\n    shapes::traced(attribute, item)\n        .unwrap_or_else(syn::Error::into_compile_error)\n        .into()\n}\n\n/// Build a lookup table.\n#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    let input = syn::parse::<syn::ExprArray>(input)?;\n    shapes::table(&input).into()\n}\n",
                ),
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "forwarder to another crate's function passes",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "/// Build a lookup table.\n#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    ::shape_support::expand::table::<proc_macro2::TokenStream>(input)\n}\n",
                ),
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "twenty thin entries pass when non-entry lines stay under budget",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(&helpers::numbered_derive_entries(20)),
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "entry with several statements is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    let first = input.clone();\n    let second = first.clone();\n    shapes::table(second)\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "entry with an if expression is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    if input.is_empty() {\n        input\n    } else {\n        shapes::table(input)\n    }\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "entry with a match expression is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    match shapes::table(input) {\n        Ok(value) => value,\n        Err(error) => error,\n    }\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "logic packed into one call argument is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    shapes::table(input.into_iter().filter(shapes::keep).collect())\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "closure in the forwarder is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    shapes::table(input).unwrap_or_else(|error| error.to_compile_error())\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "nested function in the entry is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    fn expand(input: TokenStream) -> TokenStream {\n        input\n    }\n    expand(input)\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "second call in the forwarder is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    shapes::render(shapes::table(input))\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "cfg_attr entry attribute is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "#[cfg_attr(feature = \"tables\", proc_macro)]\npub fn table(input: TokenStream) -> TokenStream {\n    shapes::table(input)\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "non-macro function in a proc-macro root is reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    "fn table(input: TokenStream) -> TokenStream {\n    shapes::table(input)\n}\n",
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "thin entry in an ordinary library root is reported",
            repo_files: vec![helpers::library_root(
                "#[proc_macro]\npub fn table(input: TokenStream) -> TokenStream {\n    shapes::table(input)\n}\n",
            )],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "twenty-one thin entries exceed the entry cap",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(&helpers::numbered_derive_entries(21)),
            ],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "more than eighty non-entry lines are reported",
            repo_files: vec![
                helpers::proc_macro_manifest(),
                helpers::library_root(
                    &("\n".repeat(80) + &helpers::numbered_derive_entries(1)),
                ),
            ],
            expected_violation_codes: vec!["RSR406"],
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
