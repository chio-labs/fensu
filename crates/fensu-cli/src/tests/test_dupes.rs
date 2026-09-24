//! Detection primitives for the advisory dupes command.

use crate::dupes::_helpers::inputs::changes::parse_unified_diff;
use crate::dupes::_helpers::matching::fingerprints::{fingerprint_tokens, token_identifier};
use crate::dupes::_helpers::matching::sequence::{matching_blocks, ratio};
use crate::tests::helpers::{characters, python_units, rust_units, script_units, svelte_units};
use crate::tests::test_types::{
    FingerprintTestCase, SequenceRatioTestCase, UnifiedDiffTestCase, UnitExtractionTestCase,
};

const RATIO_TOLERANCE: f64 = 1e-12;

#[test]
fn given_token_sequences_when_scoring_then_ratio_matches_difflib() {
    let test_cases = [
        SequenceRatioTestCase {
            description: "one replacement and one insertion",
            left: "abcdefg",
            right: "abxdefgh",
            expected_ratio: 0.8,
            expected_blocks: &[(0, 0, 2), (3, 3, 4)],
        },
        SequenceRatioTestCase {
            description: "two scattered replacements",
            left: "the quick brown fox",
            right: "the quack brown box",
            expected_ratio: 0.894_736_842_105_263_2,
            expected_blocks: &[(0, 0, 6), (7, 7, 9), (17, 17, 2)],
        },
        SequenceRatioTestCase {
            description: "repeated tokens prefer the earliest match",
            left: "aaaa",
            right: "aa",
            expected_ratio: 0.666_666_666_666_666_6,
            expected_blocks: &[(0, 0, 2)],
        },
        SequenceRatioTestCase {
            description: "disjoint sequences",
            left: "abc",
            right: "xyz",
            expected_ratio: 0.0,
            expected_blocks: &[],
        },
    ];
    for test_case in &test_cases {
        let (left, right) = (characters(test_case.left), characters(test_case.right));

        let score = ratio(&left, &right);
        let blocks = matching_blocks(&left, &right)
            .iter()
            .map(|block| (block.left_start, block.right_start, block.size))
            .collect::<Vec<_>>();

        assert!(
            (score - test_case.expected_ratio).abs() < RATIO_TOLERANCE,
            "{}: {score}",
            test_case.description
        );
        assert_eq!(
            blocks, test_case.expected_blocks,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_normalised_tokens_when_fingerprinting_then_hashes_match_the_reference() {
    let test_cases = [
        FingerprintTestCase {
            description: "one k-gram yields its CPython tuple hash",
            tokens: &[
                "def", "$id", "(", "$id", ",", "$id", ")", ":", "$nl", "$in", "return", "$id",
            ],
            expected_fingerprints: &[-529_448_090_286_596_742],
        },
        FingerprintTestCase {
            description: "streams shorter than one k-gram have no fingerprints",
            tokens: &["def", "$id"],
            expected_fingerprints: &[],
        },
    ];
    for test_case in &test_cases {
        let identifiers = test_case
            .tokens
            .iter()
            .map(|token| token_identifier(token))
            .collect::<Vec<_>>();

        let fingerprints = fingerprint_tokens(&identifiers)
            .into_iter()
            .collect::<Vec<_>>();

        assert_eq!(
            token_identifier("$id"),
            1_055_212_161,
            "{}",
            test_case.description
        );
        assert_eq!(
            fingerprints, test_case.expected_fingerprints,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_zero_context_git_diff_when_parsing_then_added_ranges_and_deletions_are_kept() {
    let test_cases = [UnifiedDiffTestCase {
        description: "additions, single-line hunks, deletions, and removed files",
        diff: "diff --git a/src/orders.py b/src/orders.py\n--- a/src/orders.py\n+++ b/src/orders.py\n@@ -3,0 +4,2 @@ def total():\n+    a\n+    b\n@@ -9 +11 @@\n-x\n+y\n@@ -20,2 +21,0 @@\n-gone\n-gone\ndiff --git a/src/old.py b/src/old.py\n--- a/src/old.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-a\n-b\n",
        expected_changes: &[("src/orders.py", &[(4, 5), (11, 11)], &[21])],
    }];
    for test_case in &test_cases {
        let parsed = parse_unified_diff(test_case.diff);

        let mut changes = parsed
            .iter()
            .map(|(path, change)| {
                (
                    path.as_str(),
                    change.added_ranges.as_slice(),
                    change.deletion_points.as_slice(),
                )
            })
            .collect::<Vec<_>>();
        changes.sort();

        assert_eq!(
            changes, test_case.expected_changes,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_language_sources_when_extracting_units_then_names_lines_and_tokens_are_normalised() {
    let test_cases = [
        UnitExtractionTestCase {
            description: "python drops decorators, docstrings, annotations, and keeps call targets",
            extract: python_units,
            path: "orders.py",
            source: "class Orders:\n    class Audit:\n        def check(self): pass\n\n    @cached\n    def total(self, rate: float) -> float:\n        \"\"\"Docstring.\"\"\"\n        amount: int = compute(rate, 2)\n        return self.scale(amount, f\"{rate}x\")\n",
            expected_units: &[
                ("Orders.Audit.check", 3, 3, "def $id ( $id ) : pass"),
                ("Orders.total", 6, 9, "def $id ( $id , $id ) : $nl $in $id = compute ( $id , $num ) $nl return $id . scale ( $id , $fstr { $id } )"),
            ],
        },
        UnitExtractionTestCase {
            description: "rust merges operators and lifetimes, drops doc comments, and skips test items",
            extract: rust_units,
            path: "crates/shop/src/orders.rs",
            source: "impl<'a> Ledger<'a> {\n    /// Totals.\n    pub fn total(&self, rate: &'a u64) -> u64 {\n        let x = r#\"raw\"# ;\n        if *rate >= 2 { compute!(x, b'a') } else { self.scale(1.5) }\n    }\n}\n#[cfg(test)]\nfn helper() {}\n#[tokio::test]\nasync fn checks() {}\n",
            expected_units: &[(
                "Ledger::total",
                3,
                6,
                "fn $id ( & self , $id : & $life $id ) -> $id { let $id = $str ; if * $id >= $num { compute ! ( $id , $byte ) } else { self . scale ( $num ) } }",
            )],
        },
        UnitExtractionTestCase {
            description: "typescript units cover functions, arrow constants, and class members",
            extract: script_units,
            path: "src/orders.ts",
            source: "export const total = (rate: number): number => compute(rate, `x${rate}`);\nclass Orders {\n  @logged\n  scale(value: number) { return this.#apply(value, /x/g); }\n}\n",
            expected_units: &[
                ("total", 1, 1, "const $id = ( $id ) => compute ( $id , $tpl $id )"),
                ("Orders.scale", 4, 4, "$id ( $id ) { return this . #apply ( $id , $re ) ; }"),
            ],
        },
        UnitExtractionTestCase {
            description: "svelte script units report component line numbers",
            extract: svelte_units,
            path: "src/Orders.svelte",
            source: "<h1>Orders</h1>\n<script lang=\"ts\">\n  function total(rate: number) {\n    return compute(rate);\n  }\n</script>\n",
            expected_units: &[("total", 3, 5, "function $id ( $id ) { return compute ( $id ) ; }")],
        },
    ];
    for test_case in &test_cases {
        let units = (test_case.extract)(test_case.path, test_case.source);

        let joined = units
            .iter()
            .map(|unit| unit.normalized.join(" "))
            .collect::<Vec<_>>();
        let summary = units
            .iter()
            .zip(&joined)
            .map(|(unit, tokens)| {
                (
                    unit.name.as_str(),
                    unit.start_line,
                    unit.end_line,
                    tokens.as_str(),
                )
            })
            .collect::<Vec<_>>();

        assert_eq!(
            summary, test_case.expected_units,
            "{}",
            test_case.description
        );
    }
}
