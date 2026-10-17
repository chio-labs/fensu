use crate::helpers::{run_check, run_check_with, write};
use crate::test_types::{RustCacheTestCase, RustSymbolExceptionTestCase};

const ITEMS: &str = "pub fn free(value: (u8, u8, u8, u8)) -> u8 { value.0 }\npub fn other(value: (u8, u8, u8, u8)) -> u8 { value.0 }\npub struct Record { pub value: (u8, u8, u8, u8) }\npub enum Choice { Value((u8, u8, u8, u8)) }\npub trait Source { fn read(&self) -> (u8, u8, u8, u8); }\npub trait Fallback { fn fetch(&self) -> (u8, u8, u8, u8) { (0, 0, 0, 0) } }\nimpl Record { pub fn load(&self) -> (u8, u8, u8, u8) { self.value } }\npub mod inner { pub fn nested(value: (u8, u8, u8, u8)) -> u8 { value.0 } }\n";
const ITEM_LINES: &[&str] = &[
    "src/lib.rs:1:",
    "src/lib.rs:2:",
    "src/lib.rs:3:",
    "src/lib.rs:4:",
    "src/lib.rs:5:",
    "src/lib.rs:6:",
    "src/lib.rs:7:",
    "src/lib.rs:8:",
];
const DOCUMENTED: &str = "/// First summary line.\n/// Second summary line.\npub fn documented() -> u8 { 1 }\n/// First summary line.\n/// Second summary line.\npub fn plain() -> u8 { 1 }\n";
const ATTRIBUTED: &str = "#[inline] // first note\npub fn attributed() -> u8 { 1 }\n#[inline] // second note\npub fn plain() -> u8 { 1 }\n";
const TRAIT_IMPLS: &str = "pub trait First { fn run(&self); }\npub trait Second { fn run(&self); }\npub struct Record;\nimpl First for Record { fn run(&self) {} }\nimpl Second for Record { fn run(&self) {} }\n";

#[test]
fn given_rust_symbol_exception_when_checking_then_only_faults_inside_the_symbol_span_are_suppressed(
) {
    let test_cases = [
        RustSymbolExceptionTestCase {
            description: "free function",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"free\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:2:"],
            expected_absent: &["src/lib.rs:1:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "struct",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"Record\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:2:", "src/lib.rs:7:"],
            expected_absent: &["src/lib.rs:3:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "enum",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"Choice\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:2:"],
            expected_absent: &["src/lib.rs:4:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "trait",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"Source\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:2:"],
            expected_absent: &["src/lib.rs:5:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "trait default method",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"Fallback::fetch\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:2:"],
            expected_absent: &["src/lib.rs:6:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "inherent method",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"Record::load\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:2:", "src/lib.rs:3:"],
            expected_absent: &["src/lib.rs:7:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "inline module item",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"inner::nested\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:2:"],
            expected_absent: &["src/lib.rs:8:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "doc-comment line of the item",
            source: DOCUMENTED,
            select: "FPRSH001",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSH001\"\nsymbols = [\"documented\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:4:"],
            expected_absent: &["src/lib.rs:1:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "attribute line of the item",
            source: ATTRIBUTED,
            select: "FPRSH002",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSH002\"\nsymbols = [\"attributed\"]\n",
            expected_exit_code: 1,
            expected_present: &["src/lib.rs:3:"],
            expected_absent: &["src/lib.rs:1:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "file-level exception remains unchanged",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\n",
            expected_exit_code: 0,
            expected_present: &["Found 0 faults"],
            expected_absent: ITEM_LINES,
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "file-level exception still suppresses a line-less fault",
            source: ITEMS,
            select: "FPRSR601",
            options: "[targets.rust.rule_options.FPRSR601]\nmax_file_lines = 1\n",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSR601\"\n",
            expected_exit_code: 0,
            expected_present: &["Found 0 faults"],
            expected_absent: &["FPRSR601"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "line-less fault is not suppressed by a symbol and the symbol is stale",
            source: ITEMS,
            select: "FPRSR601",
            options: "[targets.rust.rule_options.FPRSR601]\nmax_file_lines = 1\n",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSR601\"\nsymbols = [\"free\"]\n",
            expected_exit_code: 2,
            expected_present: &[],
            expected_absent: &[],
            expected_stderr: "Rule exception no longer matches a fault: FPRSR601 src/lib.rs::free.",
        },
        RustSymbolExceptionTestCase {
            description: "each listed symbol suppresses its own fault",
            source: DOCUMENTED,
            select: "FPRSH001",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSH001\"\nsymbols = [\"documented\", \"plain\"]\n",
            expected_exit_code: 0,
            expected_present: &["Found 0 faults"],
            expected_absent: &["src/lib.rs:1:", "src/lib.rs:4:"],
            expected_stderr: "",
        },
        RustSymbolExceptionTestCase {
            description: "existing symbol without a fault is stale",
            source: ATTRIBUTED,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"attributed\"]\n",
            expected_exit_code: 2,
            expected_present: &[],
            expected_absent: &[],
            expected_stderr: "Rule exception no longer matches a fault: FPRSS012 src/lib.rs::attributed.",
        },
        RustSymbolExceptionTestCase {
            description: "missing symbol is rejected",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"absent\"]\n",
            expected_exit_code: 2,
            expected_present: &[],
            expected_absent: &[],
            expected_stderr: "Rule exception symbol does not exist in src/lib.rs: absent.",
        },
        RustSymbolExceptionTestCase {
            description: "method name shared by two trait impls is ambiguous",
            source: TRAIT_IMPLS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"Record::run\"]\n",
            expected_exit_code: 2,
            expected_present: &[],
            expected_absent: &[],
            expected_stderr: "Rule exception symbol is ambiguous in src/lib.rs: Record::run.",
        },
        RustSymbolExceptionTestCase {
            description: "Cargo.toml exception rejects symbol scope",
            source: ITEMS,
            select: "FPRSL302",
            options: "",
            exception: "path = \"Cargo.toml\"\nrule = \"FPRSL302\"\nsymbols = [\"free\"]\n",
            expected_exit_code: 2,
            expected_present: &[],
            expected_absent: &[],
            expected_stderr: "Rust Cargo.toml rule exceptions support file-level exceptions only: Cargo.toml.",
        },
        RustSymbolExceptionTestCase {
            description: "dotted symbol paths are malformed for Rust",
            source: ITEMS,
            select: "FPRSS012",
            options: "",
            exception: "path = \"src/lib.rs\"\nrule = \"FPRSS012\"\nsymbols = [\"Record.load\"]\n",
            expected_exit_code: 2,
            expected_present: &[],
            expected_absent: &[],
            expected_stderr: "Malformed qualified rule exception symbol: Record.load.",
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(repository.path().join("src/lib.rs"), test_case.source);
        write(
            repository.path().join("fensu.toml"),
            &format!(
                "[targets.rust]\nanalyzer = \"rust\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_packs = [\"rust\"]\nselect = [\"{}\"]\n{}[[targets.rust.rule_exceptions]]\n{}reason = \"External callers rely on this shape.\"\n",
                test_case.select, test_case.options, test_case.exception
            ),
        );

        let output = run_check(repository.path());
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        for expected in test_case.expected_present {
            assert!(
                stdout.contains(expected),
                "{}: {expected} in {stdout}",
                test_case.description
            );
        }
        for unexpected in test_case.expected_absent {
            assert!(
                !stdout.contains(unexpected),
                "{}: {unexpected} in {stdout}",
                test_case.description
            );
        }
        assert!(
            stderr.contains(test_case.expected_stderr),
            "{}: {stderr}",
            test_case.description
        );
    }
}

#[test]
fn given_cached_rust_symbol_exception_when_symbol_layout_changes_then_cached_result_is_not_reused()
{
    let test_cases = [RustCacheTestCase {
        description: "moving the fault outside the symbol invalidates the source fingerprint",
        expected_cold: "Cache: hits=0 misses=1",
        expected_warm: "Cache: hits=1 misses=0",
        expected_invalidated:
            "Rule exception no longer matches a fault: FPRSS012 src/lib.rs::free.",
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            repository.path().join("src/lib.rs"),
            "pub fn free(value: (u8, u8, u8, u8)) -> u8 { value.0 }\npub fn other() -> u8 { 1 }\n",
        );
        write(
            repository.path().join("fensu.toml"),
            "[targets.rust]\nanalyzer = \"rust\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_packs = [\"rust\"]\nselect = [\"FPRSS012\"]\n[[targets.rust.rule_exceptions]]\nrule = \"FPRSS012\"\npath = \"src/lib.rs\"\nsymbols = [\"free\"]\nreason = \"External callers rely on this shape.\"\n",
        );

        let cold = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        let warm = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        write(
            repository.path().join("src/lib.rs"),
            "pub fn free() -> u8 { 1 }\npub fn other(value: (u8, u8, u8, u8)) -> u8 { value.0 }\n",
        );
        let invalidated = run_check_with(repository.path(), &["--cache", "--cache-stats"]);
        let cold_stderr = String::from_utf8_lossy(&cold.stderr);
        let warm_stderr = String::from_utf8_lossy(&warm.stderr);
        let invalidated_stderr = String::from_utf8_lossy(&invalidated.stderr);

        assert!(
            cold_stderr.contains(test_case.expected_cold),
            "{}: {cold_stderr}",
            test_case.description
        );
        assert!(
            warm_stderr.contains(test_case.expected_warm),
            "{}: {warm_stderr}",
            test_case.description
        );
        assert!(
            invalidated_stderr.contains(test_case.expected_invalidated),
            "{}: {invalidated_stderr}",
            test_case.description
        );
    }
}
