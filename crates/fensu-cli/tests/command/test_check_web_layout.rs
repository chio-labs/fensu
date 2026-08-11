use crate::helpers::{poison_processes, run_internal_web_check_with, write};
use crate::test_types::WebSourcePurposeTestCase;

const VALID_TYPESCRIPT: &str = "export const value: number = 2;\n";

#[test]
fn given_web_test_layout_when_checking_fwt002_then_enforces_selected_ownership_model() {
    let test_cases = [
        WebSourcePurposeTestCase {
            description: "colocated TypeScript test is adjacent to its source",
            config: "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FPTST002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/orders.ts", VALID_TYPESCRIPT),
                ("src/orders.test.ts", "test('orders', () => {});\n"),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FPTST002"),
        },
        WebSourcePurposeTestCase {
            description: "colocated Svelte component test is adjacent to its source",
            config: "[targets.web]\nanalyzer = \"svelte\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FPTST002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/Card.svelte", "<p>card</p>\n"),
                ("src/Card.test.ts", "test('card', () => {});\n"),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FPTST002"),
        },
        WebSourcePurposeTestCase {
            description: "colocated tooling spec is adjacent to its tooling source",
            config: "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = []\ntooling = [\"scripts\"]\ntest_layout = \"colocated\"\nselect = [\"FPTST002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/value.ts", VALID_TYPESCRIPT),
                ("scripts/catalogue.ts", VALID_TYPESCRIPT),
                ("scripts/catalogue.spec.ts", "test('catalogue', () => {});\n"),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FPTST002"),
        },
        WebSourcePurposeTestCase {
            description: "recognized colocated setup test is accepted without a source counterpart",
            config: "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FPTST002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[("src/setup.test.ts", "beforeEach(() => {});\n")],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FPTST002"),
        },
        WebSourcePurposeTestCase {
            description: "arbitrary runtime setup module remains runtime policy",
            config: "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FPTSH009\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[("src/setup.ts", "setup();\n")],
            expected_exit_code: 1,
            expected_present: Some("FPTSH009"),
            expected_absent: None,
        },
        WebSourcePurposeTestCase {
            description: "explicit mirrored layout rejects a non-mirroring configured test",
            config: "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\ntest_layout = \"mirrored\"\nselect = [\"FPTST002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/orders.ts", VALID_TYPESCRIPT),
                ("tests/orphan/orders.test.ts", "test('orders', () => {});\n"),
            ],
            expected_exit_code: 1,
            expected_present: Some("FPTST002"),
            expected_absent: None,
        },
        WebSourcePurposeTestCase {
            description: "colocated layout rejects a mirrored test",
            config: "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FPTST002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/orders.ts", VALID_TYPESCRIPT),
                ("tests/src/orders.test.ts", "test('orders', () => {});\n"),
            ],
            expected_exit_code: 1,
            expected_present: Some("FPTST002"),
            expected_absent: None,
        },
        WebSourcePurposeTestCase {
            description: "colocated near miss with a different source stem is rejected",
            config: "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FPTST002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/orders.ts", VALID_TYPESCRIPT),
                ("src/order.test.ts", "test('order', () => {});\n"),
            ],
            expected_exit_code: 1,
            expected_present: Some("FPTST002"),
            expected_absent: None,
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        for (path, source) in test_case.files {
            write(repository.path().join(path), source);
        }
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert_eq!(
            test_case
                .expected_present
                .is_some_and(|code| stdout.contains(code)),
            test_case.expected_present.is_some(),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            test_case
                .expected_absent
                .is_none_or(|code| !stdout.contains(code)),
            "{}: {stdout}",
            test_case.description
        );
    }
}
